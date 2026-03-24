"""E-Invoicing Service — SRI Ecuador Integration

Covers:
- RUC/cédula validation
- SOAP envelope building for RecepcionComprobantesOffline
- SOAP envelope building for AutorizacionComprobantesOffline
- Parsing both reception and authorization SOAP responses
- DB-backed settings via EInvoicingCountrySettings (same pattern as SIIService)
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.einvoicing.country_settings import EInvoicingCountrySettings

logger = logging.getLogger(__name__)

# SRI SOAP namespaces
_NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
_NS_RECEPCION = "http://ec.gob.sri.ws.recepcion"
_NS_AUTORIZACION = "http://ec.gob.sri.ws.autorizacion"

# Default SRI endpoints (used only when DB settings have no api_endpoint)
_SRI_ENDPOINTS: dict[str, dict[str, str]] = {
    "sandbox": {
        "recepcion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
        "autorizacion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
    },
    "production": {
        "recepcion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
        "autorizacion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
    },
}


# ---------------------------------------------------------------------------
# RUC / Cédula Validation
# ---------------------------------------------------------------------------


def _validate_cedula_ec(cedula: str) -> bool:
    """Validar cédula ecuatoriana (10 dígitos) con algoritmo módulo 10."""
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    province = int(cedula[:2])
    if province < 1 or province > 24:
        return False
    coeffs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = sum((v - 9 if v >= 10 else v) for v in (int(cedula[i]) * coeffs[i] for i in range(9)))
    check = (10 - (total % 10)) % 10
    return check == int(cedula[9])


def _validate_ruc_public(ruc: str) -> bool:
    """Validar RUC de entidad pública (tercer dígito = 6), módulo 11."""
    if len(ruc) != 13 or not ruc.isdigit():
        return False
    coeffs = [3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(ruc[i]) * coeffs[i] for i in range(8))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        return False
    return check == int(ruc[8]) and ruc[9:] != "000"


def _validate_ruc_juridico(ruc: str) -> bool:
    """Validar RUC de persona jurídica (tercer dígito = 9), módulo 11."""
    if len(ruc) != 13 or not ruc.isdigit():
        return False
    coeffs = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(ruc[i]) * coeffs[i] for i in range(9))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        return False
    return check == int(ruc[9]) and ruc[10:] != "000"


def validate_ruc_ec(ruc: str) -> bool:
    """
    Validar RUC ecuatoriano (13 dígitos).
    Cubre: persona natural, persona jurídica y entidad pública.
    """
    if not ruc or len(ruc) != 13 or not ruc.isdigit():
        return False
    province = int(ruc[:2])
    if province < 1 or province > 24:
        return False
    third = int(ruc[2])
    if third < 6:
        # Persona natural: validar cédula (primeros 10) + establecimiento != 000
        return _validate_cedula_ec(ruc[:10]) and ruc[10:] != "000"
    if third == 6:
        return _validate_ruc_public(ruc)
    if third == 9:
        return _validate_ruc_juridico(ruc)
    return False


# ---------------------------------------------------------------------------
# SOAP Envelope Builders
# ---------------------------------------------------------------------------


def _build_reception_envelope(signed_xml: str) -> str:
    """Construir SOAP envelope para RecepcionComprobantesOffline."""
    import base64

    xml_b64 = base64.b64encode(signed_xml.encode("utf-8")).decode()
    return (
        f'<soapenv:Envelope xmlns:soapenv="{_NS_SOAP}" xmlns:ec="{_NS_RECEPCION}">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        "<ec:validarComprobante>"
        f"<xml>{xml_b64}</xml>"
        "</ec:validarComprobante>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


def _build_authorization_envelope(clave_acceso: str) -> str:
    """Construir SOAP envelope para AutorizacionComprobantesOffline."""
    return (
        f'<soapenv:Envelope xmlns:soapenv="{_NS_SOAP}" xmlns:ec="{_NS_AUTORIZACION}">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        "<ec:autorizacionComprobante>"
        f"<claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>"
        "</ec:autorizacionComprobante>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


# ---------------------------------------------------------------------------
# SOAP Response Parsers
# ---------------------------------------------------------------------------


def _parse_reception_response(raw_text: str) -> dict[str, str | list | None]:
    """
    Parsear respuesta SOAP de RecepcionComprobantesOffline.
    Estado posible: RECIBIDA | DEVUELTA
    """
    result: dict[str, str | list | None] = {
        "status": "ERROR",
        "clave_acceso": None,
        "messages": [],
    }
    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError:
        result["raw"] = raw_text[:500]
        return result

    # Strip namespaces
    def _tag(elem: ET.Element) -> str:
        return elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag

    for elem in root.iter():
        tag = _tag(elem)
        text = (elem.text or "").strip()
        if tag == "estado" and text:
            result["status"] = "RECEIVED" if text.upper() == "RECIBIDA" else "REJECTED"
        elif tag == "claveAcceso" and text:
            result["clave_acceso"] = text

    # Collect error messages
    messages = []
    for msg in root.iter():
        if _tag(msg) == "mensaje":
            tipo = msg.find("./tipo")
            texto = msg.find("./mensaje")
            info = msg.find("./informacionAdicional")
            messages.append(
                {
                    "tipo": (tipo.text or "").strip() if tipo is not None else "",
                    "mensaje": (texto.text or "").strip() if texto is not None else "",
                    "info": (info.text or "").strip() if info is not None else "",
                }
            )
    result["messages"] = [m for m in messages if m["tipo"] or m["mensaje"]]
    return result


def _parse_authorization_response(raw_text: str) -> dict[str, str | None]:
    """
    Parsear respuesta SOAP de AutorizacionComprobantesOffline.
    Estado posible: AUTORIZADO | NO AUTORIZADO
    """
    result: dict[str, str | None] = {
        "status": "ERROR",
        "authorization_number": None,
        "authorization_date": None,
        "environment": None,
        "authorized_xml": None,
        "message": None,
    }
    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError:
        result["message"] = raw_text[:500]
        return result

    def _tag(elem: ET.Element) -> str:
        return elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag

    for elem in root.iter():
        tag = _tag(elem)
        text = (elem.text or "").strip()
        if not text:
            continue
        if tag == "estado":
            result["status"] = "AUTHORIZED" if text.upper() == "AUTORIZADO" else "REJECTED"
        elif tag == "numeroAutorizacion":
            result["authorization_number"] = text
        elif tag == "fechaAutorizacion":
            result["authorization_date"] = text
        elif tag == "ambiente":
            result["environment"] = text
        elif tag == "comprobante":
            result["authorized_xml"] = text  # CDATA content

    # Error messages
    msgs = []
    for msg in root.iter():
        if _tag(msg) == "mensaje":
            texto = msg.find("./mensaje")
            if texto is not None and (texto.text or "").strip():
                msgs.append((texto.text or "").strip())
    if msgs:
        result["message"] = " | ".join(msgs[:3])

    return result


# ---------------------------------------------------------------------------
# SRIService
# ---------------------------------------------------------------------------


class SRIService:
    """
    Servicio para integración con SRI Ecuador.
    Espeja el patrón de SIIService (España) usando EInvoicingCountrySettings.
    """

    @staticmethod
    def get_settings(
        db: Session, tenant_id: UUID, country: str = "EC"
    ) -> EInvoicingCountrySettings:
        """Obtiene configuración desde BD."""
        settings = db.execute(
            select(EInvoicingCountrySettings).where(
                EInvoicingCountrySettings.tenant_id == tenant_id,
                EInvoicingCountrySettings.country == country,
            )
        ).scalar_one_or_none()
        if not settings:
            raise ValueError(f"SRI settings not configured for tenant {tenant_id}")
        if not settings.is_enabled:
            raise ValueError(f"E-Invoicing (SRI) not enabled for tenant {tenant_id}")
        return settings

    @staticmethod
    def _get_endpoints(settings: EInvoicingCountrySettings) -> dict[str, str]:
        """Obtiene endpoints de recepción y autorización desde settings o defaults."""
        env = (settings.environment or "STAGING").lower()
        env_key = "production" if env == "production" else "sandbox"
        defaults = _SRI_ENDPOINTS[env_key]

        validation_rules = settings.validation_rules or {}
        return {
            "recepcion": validation_rules.get("recepcion_endpoint")
            or settings.api_endpoint
            or defaults["recepcion"],
            "autorizacion": validation_rules.get("autorizacion_endpoint")
            or defaults["autorizacion"],
        }

    @staticmethod
    def validate_invoice_data(invoice_data: dict) -> list[str]:
        """Pre-validar datos antes de enviar al SRI."""
        errors: list[str] = []
        empresa = invoice_data.get("empresa", {})
        cliente = invoice_data.get("cliente", {})

        ruc_empresa = empresa.get("ruc", "")
        if not validate_ruc_ec(ruc_empresa):
            errors.append(f"ruc_empresa_invalido: {ruc_empresa!r}")

        ruc_cliente = cliente.get("ruc", "")
        if ruc_cliente and len(ruc_cliente) in (10, 13):
            if len(ruc_cliente) == 13 and not validate_ruc_ec(ruc_cliente):
                errors.append(f"ruc_cliente_invalido: {ruc_cliente!r}")
            elif len(ruc_cliente) == 10 and not _validate_cedula_ec(ruc_cliente):
                errors.append(f"cedula_cliente_invalida: {ruc_cliente!r}")

        if not invoice_data.get("numero"):
            errors.append("numero_factura_requerido")
        if not invoice_data.get("fecha"):
            errors.append("fecha_factura_requerida")
        if not invoice_data.get("lines"):
            errors.append("lineas_factura_requeridas")

        return errors

    @staticmethod
    def send_reception(
        settings: EInvoicingCountrySettings,
        signed_xml: str,
        *,
        timeout: float = 30.0,
    ) -> dict[str, str | list | None]:
        """Enviar XML firmado a RecepcionComprobantesOffline."""
        endpoints = SRIService._get_endpoints(settings)
        url = endpoints["recepcion"]
        envelope = _build_reception_envelope(signed_xml)

        validation_rules = settings.validation_rules or {}
        verify_ssl = bool(validation_rules.get("verify_ssl", True))

        try:
            with httpx.Client(timeout=timeout, verify=verify_ssl) as client:
                response = client.post(
                    url,
                    content=envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "",
                    },
                )
        except httpx.RequestError as exc:
            logger.error("SRI reception HTTP error: %s", exc)
            return {"status": "ERROR", "message": str(exc)}

        if response.status_code != 200:
            return {"status": "ERROR", "message": f"HTTP {response.status_code}"}

        return _parse_reception_response(response.text)

    @staticmethod
    def poll_authorization(
        settings: EInvoicingCountrySettings,
        clave_acceso: str,
        *,
        timeout: float = 20.0,
    ) -> dict[str, str | None]:
        """Consultar autorización en AutorizacionComprobantesOffline."""
        endpoints = SRIService._get_endpoints(settings)
        url = endpoints["autorizacion"]
        envelope = _build_authorization_envelope(clave_acceso)

        validation_rules = settings.validation_rules or {}
        verify_ssl = bool(validation_rules.get("verify_ssl", True))

        try:
            with httpx.Client(timeout=timeout, verify=verify_ssl) as client:
                response = client.post(
                    url,
                    content=envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "",
                    },
                )
        except httpx.RequestError as exc:
            logger.error("SRI authorization HTTP error: %s", exc)
            return {"status": "ERROR", "message": str(exc)}

        if response.status_code != 200:
            return {"status": "ERROR", "message": f"HTTP {response.status_code}"}

        return _parse_authorization_response(response.text)
