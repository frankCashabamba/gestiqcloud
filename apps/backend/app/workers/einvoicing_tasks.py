"""
E-invoicing Celery Tasks - SRI Ecuador & Facturae España
"""

import base64
import logging
import os
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.modules.einvoicing.application.facturae_xml import generate_facturae_xml

# Celery is optional in the minimal test environment. Provide light shims so
# importing this module doesn't fail when celery isn't installed.
_MINIMAL = str(os.getenv("TEST_MINIMAL", "0")).lower() in ("1", "true", "yes")

try:  # pragma: no cover - trivial shim when TEST_MINIMAL
    from celery import Task  # type: ignore
except Exception:  # pragma: no cover
    if _MINIMAL:

        class Task:  # minimal base class to satisfy attribute access
            autoretry_for: tuple[Any, ...] = ()
            retry_kwargs: dict[str, Any] = {}
            retry_backoff: bool = False

    else:
        raise

logger = logging.getLogger(__name__)


class EInvoicingTask(Task):
    """Base task con manejo de errors"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True


# ============================================================================
# SRI Ecuador
# ============================================================================


def generate_sri_xml(invoice_data: dict[str, Any]) -> str:
    """
    Generar XML RIDE conforme a XSD SRI Ecuador.
    Versión simplificada para MVP - expandir según especificación completa.
    """
    from lxml import etree

    def _normalize_rate(raw: Any) -> Decimal:
        try:
            rate = Decimal(str(raw)) if raw is not None else Decimal("0")
        except Exception:
            return Decimal("0")
        if rate > 1:
            rate = rate / Decimal("100")
        if rate < 0:
            rate = Decimal("0")
        return rate

    def _resolve_invoice_rate() -> Decimal:
        raw = invoice_data.get("tax_rate") or invoice_data.get("iva_rate")
        if raw is not None:
            return _normalize_rate(raw)
        subtotal = invoice_data.get("subtotal") or 0
        impuesto = invoice_data.get("impuesto") or invoice_data.get("iva") or 0
        try:
            subtotal_dec = Decimal(str(subtotal))
            impuesto_dec = Decimal(str(impuesto))
        except Exception:
            return Decimal("0")
        if subtotal_dec <= 0:
            return Decimal("0")
        return _normalize_rate(impuesto_dec / subtotal_dec)

    def _resolve_line_rate(line: dict[str, Any], default_rate: Decimal) -> Decimal:
        raw = line.get("tax_rate") or line.get("iva_tasa") or line.get("iva_rate")
        return _normalize_rate(raw) if raw is not None else default_rate

    def _sri_codigo_porcentaje(rate: Decimal) -> str:
        rate_pct = (rate * Decimal("100")).quantize(Decimal("0.01"))
        mapping = {
            Decimal("0.00"): "0",
            Decimal("12.00"): "2",
            Decimal("14.00"): "3",
            Decimal("15.00"): "4",
        }
        return mapping.get(rate_pct, "0")

    invoice_rate = _resolve_invoice_rate()

    # Estructura básica invoice SRI v1.1.0
    root = etree.Element("invoice", id="comprobante", version="1.1.0")

    # Info tributaria
    info_trib = etree.SubElement(root, "infoTributaria")
    etree.SubElement(info_trib, "ambiente").text = "1"  # 1=Pruebas, 2=Producción
    etree.SubElement(info_trib, "tipoEmision").text = "1"  # Normal
    etree.SubElement(info_trib, "razonSocial").text = invoice_data["empresa"]["nombre"]
    etree.SubElement(info_trib, "nombreComercial").text = invoice_data["empresa"]["nombre"]
    etree.SubElement(info_trib, "ruc").text = invoice_data["empresa"]["ruc"]
    etree.SubElement(info_trib, "claveAcceso").text = generate_clave_acceso(invoice_data)
    etree.SubElement(info_trib, "codDoc").text = "01"  # 01=invoice
    etree.SubElement(info_trib, "estab").text = "001"  # Establecimiento
    etree.SubElement(info_trib, "ptoEmi").text = "001"  # Punto emisión
    etree.SubElement(info_trib, "secuencial").text = invoice_data["numero"].split("-")[-1].zfill(9)
    etree.SubElement(info_trib, "dirMatriz").text = invoice_data["empresa"].get("direccion", "N/A")

    # Info invoice
    info_fact = etree.SubElement(root, "infoFactura")
    etree.SubElement(info_fact, "fechaEmision").text = invoice_data["fecha"].strftime("%d/%m/%Y")
    etree.SubElement(info_fact, "dirEstablecimiento").text = invoice_data["empresa"].get(
        "direccion", "N/A"
    )
    etree.SubElement(info_fact, "obligadoContabilidad").text = "SI"
    etree.SubElement(info_fact, "tipoIdentificacionComprador").text = "05"  # RUC
    etree.SubElement(info_fact, "razonSocialComprador").text = invoice_data["cliente"]["nombre"]
    etree.SubElement(info_fact, "identificacionComprador").text = invoice_data["cliente"]["ruc"]
    etree.SubElement(info_fact, "totalSinImpuestos").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(info_fact, "totalDescuento").text = "0.00"

    # Total con impuestos
    total_impuestos = etree.SubElement(info_fact, "totalConImpuestos")
    total_imp = etree.SubElement(total_impuestos, "totalImpuesto")
    etree.SubElement(total_imp, "codigo").text = "2"  # IVA
    etree.SubElement(total_imp, "codigoPorcentaje").text = _sri_codigo_porcentaje(invoice_rate)
    etree.SubElement(total_imp, "baseImponible").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(total_imp, "valor").text = f"{invoice_data['impuesto']:.2f}"

    etree.SubElement(info_fact, "propina").text = "0.00"
    etree.SubElement(info_fact, "importeTotal").text = f"{invoice_data['total']:.2f}"
    etree.SubElement(info_fact, "moneda").text = "DOLAR"

    # Detalles
    detalles = etree.SubElement(root, "detalles")
    for line in invoice_data["lines"]:
        detalle = etree.SubElement(detalles, "detalle")
        etree.SubElement(detalle, "codigoPrincipal").text = line["sku"] or "PROD"
        etree.SubElement(detalle, "descripcion").text = line["descripcion"]
        etree.SubElement(detalle, "cantidad").text = f"{line['cantidad']:.2f}"
        etree.SubElement(detalle, "precioUnitario").text = f"{line['precio_unitario']:.4f}"
        etree.SubElement(detalle, "descuento").text = "0.00"
        etree.SubElement(detalle, "precioTotalSinImpuesto").text = f"{line['total']:.2f}"

        # Impuestos del detalle
        impuestos = etree.SubElement(detalle, "impuestos")
        impuesto = etree.SubElement(impuestos, "impuesto")
        line_rate = _resolve_line_rate(line, invoice_rate)
        line_rate_pct = (line_rate * Decimal("100")).quantize(Decimal("0.01"))
        etree.SubElement(impuesto, "codigo").text = "2"  # IVA
        etree.SubElement(impuesto, "codigoPorcentaje").text = _sri_codigo_porcentaje(line_rate)
        etree.SubElement(impuesto, "tarifa").text = f"{line_rate_pct:.2f}"
        etree.SubElement(impuesto, "baseImponible").text = f"{line['total']:.2f}"
        try:
            base_total = Decimal(str(line["total"]))
        except Exception:
            base_total = Decimal("0")
        etree.SubElement(impuesto, "valor").text = f"{base_total * line_rate:.2f}"

    # Info adicional
    info_adicional = etree.SubElement(root, "infoAdicional")
    etree.SubElement(info_adicional, "campoAdicional", nombre="Email").text = invoice_data[
        "cliente"
    ].get("email", "N/A")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode(
        "utf-8"
    )


def generate_clave_acceso(invoice_data: dict[str, Any], ambiente: str = "1") -> str:
    """
    Generar clave de acceso SRI (49 dígitos).

    Formato (48 base + 1 verificador = 49):
      DDMMAAAA (8) + tipoCbte (2) + RUC (13) + tipoAmbiente (1)
      + estab (3) + ptoEmi (3) + secuencial (9) + codNumerico (8)
      + tipoEmision (1) = 48 dígitos → + verificador = 49
    """
    fecha = invoice_data["fecha"]
    dd = fecha.strftime("%d")
    mm = fecha.strftime("%m")
    yyyy = fecha.strftime("%Y")
    tt = "01"  # Tipo comprobante (01=factura)
    ruc = invoice_data["empresa"]["ruc"]
    # ambiente: "1" = pruebas, "2" = producción
    ee = "001"  # Establecimiento
    ppp = "001"  # Punto de emisión
    secuencial = invoice_data["numero"].split("-")[-1].zfill(9)  # 9 dígitos
    codigo_num = "12345678"  # Código numérico (8 dígitos)
    tipo_emision = "1"

    # 8+2+13+1+3+3+9+8+1 = 48 dígitos base
    parcial = f"{dd}{mm}{yyyy}{tt}{ruc}{ambiente}{ee}{ppp}{secuencial}{codigo_num}{tipo_emision}"

    # +1 dígito verificador = 49
    digito = calcular_digito_verificador_modulo11(parcial)
    return parcial + str(digito)


def calcular_digito_verificador_modulo11(cadena: str) -> int:
    """Calcular dígito verificador módulo 11"""
    factor = 2
    suma = 0

    for i in range(len(cadena) - 1, -1, -1):
        suma += int(cadena[i]) * factor
        factor = 7 if factor == 2 else factor - 1

    resto = suma % 11
    digito = 11 - resto

    if digito == 11:
        return 0
    elif digito == 10:
        return 1
    else:
        return digito


def sign_xml_xades_bes(xml_content: str, cert_data: dict[str, Any]) -> str:
    """
    Firmar XML con XAdES-BES conforme a especificación SRI Ecuador v1.1.0.

    Implementa:
    - Firma RSA-SHA256 (reemplaza el SHA-1 anterior)
    - Digest SHA-256 para documento y para SignedProperties
    - C14N http://www.w3.org/TR/2001/REC-xml-c14n-20010315
    - xades:QualifyingProperties con SigningTime y SigningCertificate
    - ds:KeyInfo con X509Certificate
    """
    import base64
    import hashlib
    import uuid as _uuid
    from datetime import UTC, datetime

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives.serialization import pkcs12
    from lxml import etree

    DS_NS = "http://www.w3.org/2000/09/xmldsig#"
    XADES_NS = "http://uri.etsi.org/01903/v1.3.2#"

    # 1. Cargar certificado P12
    p12_bytes = base64.b64decode(cert_data["p12_base64"])
    password = cert_data["password"]
    if isinstance(password, str):
        password = password.encode("utf-8")
    private_key, cert, _chain = pkcs12.load_key_and_certificates(
        p12_bytes, password, backend=default_backend()
    )

    # 2. Serializar certificado (DER → base64)
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode()
    cert_digest_b64 = base64.b64encode(hashlib.sha256(cert_der).digest()).decode()
    cert_issuer = cert.issuer.rfc4514_string()
    cert_serial = str(cert.serial_number)

    # 3. Parsear XML fuente
    root = etree.fromstring(  # nosec B320 - trusted XML generated by our own template engine
        xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
    )

    # 4. Calcular digest del documento (antes de insertar Signature)
    doc_c14n = etree.tostring(root, method="c14n")
    doc_digest_b64 = base64.b64encode(hashlib.sha256(doc_c14n).digest()).decode()

    # 5. IDs únicos
    sig_id = f"Signature-{_uuid.uuid4().hex[:8]}"
    signed_props_id = f"SignedProps-{_uuid.uuid4().hex[:8]}"
    signing_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 6. Construir xades:SignedProperties y calcular su digest
    sp_elem = etree.Element(
        f"{{{XADES_NS}}}SignedProperties",
        nsmap={"xades": XADES_NS, "ds": DS_NS},
    )
    sp_elem.set("Id", signed_props_id)
    ssp = etree.SubElement(sp_elem, f"{{{XADES_NS}}}SignedSignatureProperties")
    etree.SubElement(ssp, f"{{{XADES_NS}}}SigningTime").text = signing_time
    sc = etree.SubElement(ssp, f"{{{XADES_NS}}}SigningCertificate")
    cert_node = etree.SubElement(sc, f"{{{XADES_NS}}}Cert")
    cd = etree.SubElement(cert_node, f"{{{XADES_NS}}}CertDigest")
    etree.SubElement(
        cd,
        f"{{{DS_NS}}}DigestMethod",
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    etree.SubElement(cd, f"{{{DS_NS}}}DigestValue").text = cert_digest_b64
    is_elem = etree.SubElement(cert_node, f"{{{XADES_NS}}}IssuerSerial")
    etree.SubElement(is_elem, f"{{{DS_NS}}}X509IssuerName").text = cert_issuer
    etree.SubElement(is_elem, f"{{{DS_NS}}}X509SerialNumber").text = cert_serial

    sp_c14n = etree.tostring(sp_elem, method="c14n")
    sp_digest_b64 = base64.b64encode(hashlib.sha256(sp_c14n).digest()).decode()

    # 7. Construir ds:SignedInfo
    si_elem = etree.Element(f"{{{DS_NS}}}SignedInfo", nsmap={"ds": DS_NS})
    etree.SubElement(
        si_elem,
        f"{{{DS_NS}}}CanonicalizationMethod",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    etree.SubElement(
        si_elem,
        f"{{{DS_NS}}}SignatureMethod",
        Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    )
    # Reference al documento (enveloped: se excluye la firma al verificar)
    ref_doc = etree.SubElement(si_elem, f"{{{DS_NS}}}Reference", URI="")
    transforms = etree.SubElement(ref_doc, f"{{{DS_NS}}}Transforms")
    etree.SubElement(
        transforms,
        f"{{{DS_NS}}}Transform",
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    etree.SubElement(
        ref_doc,
        f"{{{DS_NS}}}DigestMethod",
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    etree.SubElement(ref_doc, f"{{{DS_NS}}}DigestValue").text = doc_digest_b64
    # Reference a SignedProperties
    ref_sp = etree.SubElement(
        si_elem,
        f"{{{DS_NS}}}Reference",
        URI=f"#{signed_props_id}",
        Type="http://uri.etsi.org/01903#SignedProperties",
    )
    etree.SubElement(
        ref_sp,
        f"{{{DS_NS}}}DigestMethod",
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    etree.SubElement(ref_sp, f"{{{DS_NS}}}DigestValue").text = sp_digest_b64

    # 8. Canonicalizar SignedInfo y firmar con RSA-SHA256
    si_c14n = etree.tostring(si_elem, method="c14n")
    raw_sig = private_key.sign(si_c14n, asym_padding.PKCS1v15(), hashes.SHA256())
    sig_value_b64 = base64.b64encode(raw_sig).decode()

    # 9. Ensamblar elemento ds:Signature en el documento
    sig_elem = etree.SubElement(
        root,
        f"{{{DS_NS}}}Signature",
        Id=sig_id,
        nsmap={"ds": DS_NS, "xades": XADES_NS},
    )
    sig_elem.append(si_elem)
    sv = etree.SubElement(sig_elem, f"{{{DS_NS}}}SignatureValue", Id=f"SV-{sig_id}")
    sv.text = sig_value_b64
    ki = etree.SubElement(sig_elem, f"{{{DS_NS}}}KeyInfo")
    x509d = etree.SubElement(ki, f"{{{DS_NS}}}X509Data")
    etree.SubElement(x509d, f"{{{DS_NS}}}X509Certificate").text = cert_b64

    # ds:Object → xades:QualifyingProperties → xades:SignedProperties
    obj_elem = etree.SubElement(sig_elem, f"{{{DS_NS}}}Object")
    qp = etree.SubElement(
        obj_elem,
        f"{{{XADES_NS}}}QualifyingProperties",
        Target=f"#{sig_id}",
        nsmap={"xades": XADES_NS},
    )
    qp.append(sp_elem)  # sp_elem ya fue calculado antes; se mueve aquí

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode(
        "utf-8"
    )


# Alias para compatibilidad con código existente y Facturae
sign_xml_sri = sign_xml_xades_bes


# ============================================================================
# Facturae España
# ============================================================================


def sign_facturae_xml(xml_content: str, cert_data: dict[str, Any]) -> str:
    """Firmar XML Facturae con XAdES-BES (SHA-256)."""
    return sign_xml_xades_bes(xml_content, cert_data)


# ============================================================================
# Celery Tasks
# ============================================================================

try:  # pragma: no cover
    from celery_app import celery_app  # type: ignore
except Exception:  # Provide no-op task decorator in tests when minimal
    if _MINIMAL:

        class _DummyCeleryApp:
            def task(self, *dargs, **dkwargs):
                def _decorator(fn):
                    return fn

                return _decorator

        celery_app = _DummyCeleryApp()  # type: ignore
    else:
        raise


def _load_cert_sync(tenant_id: str, country: str) -> dict[str, Any]:
    """Bridge async → sync para obtener certificado desde CertificateManager."""
    import asyncio

    from app.services.certificate_manager import certificate_manager
    from app.services.secrets import get_certificate_password

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        cert_info = loop.run_until_complete(certificate_manager.get_certificate(tenant_id, country))
    finally:
        loop.close()

    if not cert_info:
        raise ValueError(f"No certificate found for tenant {tenant_id} country={country}")

    country_code = "ECU" if country == "EC" else "ESP"
    return {
        "p12_base64": base64.b64encode(cert_info["cert_data"]).decode(),
        "password": get_certificate_password(tenant_id, country_code),
    }


@celery_app.task(base=EInvoicingTask, name="einvoicing.sign_and_send_sri")
def sign_and_send_sri_task(invoice_id: str, tenant_id: str, env: str = "sandbox"):
    """task: Firmar y enviar invoice a SRI Ecuador.

    Usa ORM + SRIService en lugar de raw SQL hardcodeado.
    """
    from uuid import UUID as _UUID

    from sqlalchemy import select

    from app.config.database import tenant_session_scope
    from app.models.core.einvoicing import SRISubmission
    from app.models.core.facturacion import Invoice
    from app.modules.einvoicing.application.sri_service import SRIService

    try:
        with tenant_session_scope(str(tenant_id)) as db:
            tid = _UUID(str(tenant_id))
            iid = _UUID(str(invoice_id))

            # 1. Obtener configuración SRI (endpoint, environment)
            sri_settings = SRIService.get_settings(db, tid, "EC")

            # 2. Cargar invoice vía ORM
            invoice = db.execute(
                select(Invoice).where(Invoice.id == iid, Invoice.tenant_id == tid)
            ).scalar_one_or_none()
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")

            tenant = invoice.tenant
            customer = invoice.customer

            # ... resto del código existente dentro del context manager

            invoice_data = {
                "numero": invoice.numero,
                "fecha": invoice.fecha or invoice.issue_date,
                "subtotal": float(invoice.subtotal or 0),
                "impuesto": float(invoice.iva or 0),
                "total": float(invoice.total or 0),
                "empresa": {
                    "nombre": getattr(tenant, "name", "") or "",
                    "ruc": getattr(tenant, "tax_id", "") or "",
                    "direccion": getattr(tenant, "address", "") or "",
                },
                "cliente": {
                    "nombre": getattr(customer, "name", "") or "",
                    "ruc": getattr(customer, "tax_id", getattr(customer, "identificacion", ""))
                    or "",
                    "email": getattr(customer, "email", "") or "",
                },
                "lines": [
                    {
                        "cantidad": float(
                            getattr(line, "cantidad", getattr(line, "quantity", 1)) or 1
                        ),
                        "precio_unitario": float(
                            getattr(line, "precio_unitario", getattr(line, "unit_price", 0)) or 0
                        ),
                        "total": float(getattr(line, "total", 0) or 0),
                        "descripcion": getattr(
                            line, "descripcion", getattr(line, "description", "")
                        )
                        or "",
                        "sku": getattr(line, "sku", None),
                    }
                    for line in (invoice.lines or [])
                ],
            }

            # 3. Pre-validar RUC antes de enviar
            from app.modules.einvoicing.application.sri_service import validate_ruc_ec

            ruc = invoice_data["empresa"]["ruc"]
            if not validate_ruc_ec(ruc):
                raise ValueError(f"RUC de empresa inválido: {ruc!r}")

            # 4. Generar XML RIDE
            xml_content = generate_sri_xml(invoice_data)
            clave_acceso = generate_clave_acceso(invoice_data)

            # 5. Cargar certificado digital
            cert_data = _load_cert_sync(tenant_id, "EC")

            # 6. Firmar con XAdES-BES (SHA-256)
            signed_xml = sign_xml_xades_bes(xml_content, cert_data)

            # 7. Enviar a RecepcionComprobantesOffline vía SRIService
            reception = SRIService.send_reception(sri_settings, signed_xml)

            # Mapear estado de recepción a estado interno
            reception_status = reception.get("status", "ERROR")
            msgs = reception.get("messages") or []
            error_msg: str | None = None
            if msgs:
                error_msg = (
                    " | ".join(m.get("mensaje", "") for m in msgs if m.get("tipo") == "ERROR")
                    or None
                )

            if reception_status == "RECEIVED":
                sri_status = "SENT"
            elif reception_status == "REJECTED":
                sri_status = "REJECTED"
                error_msg = error_msg or "Comprobante devuelto por SRI"
            else:
                sri_status = "ERROR"
                error_msg = error_msg or reception.get("message") or "Error en recepción"

            # 8. Guardar SRISubmission
            submission = SRISubmission(
                tenant_id=tid,
                invoice_id=iid,
                status=sri_status,
                receipt_number=clave_acceso,
                payload=signed_xml,
                error_message=error_msg,
            )
            db.add(submission)

            # 9. Si fue recibida, actualizar invoice y disparar polling
            if sri_status == "SENT":
                invoice.status = "einvoice_sent"

            db.commit()

            logger.info("SRI invoice %s → recepción=%s", invoice_id, sri_status)

            # 10. Programar tarea de polling de autorización (5 min)
            if sri_status == "SENT":
                poll_sri_authorization_task.apply_async(
                    args=[str(submission.id), tenant_id, clave_acceso],
                    countdown=300,
                )

            return {
                "status": sri_status,
                "clave_acceso": clave_acceso,
                "message": error_msg,
            }

    except Exception as e:
        logger.error("Error processing SRI invoice %s: %s", invoice_id, e)
        raise
    # rollback y close manejados por tenant_session_scope


@celery_app.task(name="einvoicing.poll_sri_authorization", max_retries=12)
def poll_sri_authorization_task(
    submission_id: str,
    tenant_id: str,
    clave_acceso: str,
    attempt: int = 1,
):
    """
    Consultar AutorizacionComprobantesOffline del SRI.

    Se programa 5 minutos después de la recepción exitosa y hace hasta
    12 intentos (cada 5 min ≈ 1 hora total). Cuando el SRI devuelve
    AUTORIZADO, guarda el número de autorización y actualiza el invoice.
    """
    from uuid import UUID as _UUID

    from sqlalchemy import select

    from app.config.database import SessionLocal
    from app.models.core.einvoicing import SRISubmission
    from app.models.core.facturacion import Invoice
    from app.modules.einvoicing.application.sri_service import SRIService

    MAX_ATTEMPTS = 12
    POLL_DELAY_SECONDS = 300  # 5 minutos

    db = SessionLocal()
    try:
        tid = _UUID(str(tenant_id))
        sid = _UUID(str(submission_id))

        submission = db.get(SRISubmission, sid)
        if not submission:
            logger.error("SRISubmission %s not found, cannot poll", submission_id)
            return {"status": "ERROR", "reason": "submission_not_found"}

        if submission.status == "AUTHORIZED":
            logger.info("SRISubmission %s ya autorizado, skip poll", submission_id)
            return {"status": "AUTHORIZED", "already": True}

        # Obtener settings SRI para usar endpoints configurados
        sri_settings = SRIService.get_settings(db, tid, "EC")
        auth_result = SRIService.poll_authorization(sri_settings, clave_acceso)

        auth_status = auth_result.get("status", "ERROR")

        if auth_status == "AUTHORIZED":
            submission.status = "AUTHORIZED"
            submission.authorization_number = auth_result.get("authorization_number")
            submission.response = auth_result.get("authorized_xml")
            submission.updated_at = __import__("datetime").datetime.utcnow()

            # Actualizar invoice como autorizado
            invoice = db.execute(
                select(Invoice).where(
                    Invoice.id == submission.invoice_id,
                    Invoice.tenant_id == tid,
                )
            ).scalar_one_or_none()
            if invoice:
                invoice.status = "einvoice_authorized"

            db.commit()
            logger.info(
                "SRI invoice %s AUTORIZADO — num_autorizacion=%s",
                submission.invoice_id,
                submission.authorization_number,
            )
            return {
                "status": "AUTHORIZED",
                "authorization_number": submission.authorization_number,
            }

        if auth_status == "REJECTED":
            submission.status = "REJECTED"
            submission.error_message = auth_result.get("message") or "Rechazado por SRI"
            submission.updated_at = __import__("datetime").datetime.utcnow()
            db.commit()
            logger.warning(
                "SRI invoice %s RECHAZADO: %s", submission.invoice_id, submission.error_message
            )
            return {"status": "REJECTED", "message": submission.error_message}

        # Todavía pendiente (status == ERROR o desconocido)
        db.close()
        if attempt < MAX_ATTEMPTS:
            logger.info(
                "SRI invoice %s aún pendiente (intento %d/%d), reprogramando en %ds",
                submission.invoice_id,
                attempt,
                MAX_ATTEMPTS,
                POLL_DELAY_SECONDS,
            )
            poll_sri_authorization_task.apply_async(
                args=[submission_id, tenant_id, clave_acceso, attempt + 1],
                countdown=POLL_DELAY_SECONDS,
            )
        else:
            logger.error(
                "SRI invoice %s no autorizado tras %d intentos",
                submission.invoice_id,
                MAX_ATTEMPTS,
            )
            submission.status = "ERROR"
            submission.error_message = f"Sin autorización tras {MAX_ATTEMPTS} intentos"
            submission.updated_at = __import__("datetime").datetime.utcnow()
            db.commit()

        return {"status": "PENDING", "attempt": attempt, "message": auth_result.get("message")}

    except Exception as e:
        db.rollback()
        logger.error("Error polling SRI authorization for %s: %s", submission_id, e)
        raise

    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task(base=EInvoicingTask, name="einvoicing.sign_and_send_facturae")
def sign_and_send_facturae_task(invoice_id: str, tenant_id: str, env: str = "sandbox"):
    """task: Firmar y enviar Facturae España"""
    import asyncio

    from sqlalchemy import text

    from app.config.database import SessionLocal

    db = SessionLocal()
    try:
        logger.info(f"Facturae task started: {invoice_id} for tenant {tenant_id}")

        # 1. Obtener datos de invoice
        query = text(
            """
            SELECT
                f.id, f.numero, f.fecha, f.subtotal, f.iva, f.total,
                t.name as empresa_nombre, t.tax_id as empresa_ruc,
                t.address as empresa_direccion,
                c.name as cliente_nombre, c.identificacion as cliente_ruc,
                c.email as cliente_email
            FROM invoices f
            JOIN tenants t ON t.id = f.tenant_id

            JOIN clientes c ON c.id = f.cliente_id
            WHERE f.id = :invoice_id AND f.tenant_id = :tenant_id
        """
        )

        invoice = db.execute(query, {"invoice_id": invoice_id, "tenant_id": tenant_id}).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # 2. Preparar datos y generar XML Facturae
        invoice_data = {
            "numero": invoice[1],
            "fecha": invoice[2],
            "subtotal": invoice[3],
            "iva": invoice[4],
            "total": invoice[5],
            "empresa": {
                "nombre": invoice[6],
                "ruc": invoice[7],
                "direccion": invoice[8],
            },
            "cliente": {"nombre": invoice[9], "ruc": invoice[10], "email": invoice[11]},
        }
        xml_content = generate_facturae_xml(invoice_data)

        # 3. Firmar (bridge async -> sync)
        from app.services.certificate_manager import certificate_manager

        def _get_cert():
            return loop.run_until_complete(certificate_manager.get_certificate(tenant_id, "ES"))

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cert_info = _get_cert()
        finally:
            try:
                loop.close()
            except Exception:
                pass

        if not cert_info:
            raise ValueError(f"No certificate found for tenant {tenant_id} in Spain")

        # Import secrets manager
        from app.services.secrets import get_certificate_password

        cert_data = {
            "p12_base64": base64.b64encode(cert_info["cert_data"]).decode(),
            "password": get_certificate_password(tenant_id, "ESP"),
        }
        signed_xml = sign_facturae_xml(xml_content, cert_data)

        # 4. Enviar a AEAT/SII usando endpoint configurable
        from app.modules.einvoicing.application.sii_service import SIIService

        settings = SIIService.get_settings(db, UUID(str(tenant_id)), "ES")
        result = SIIService.submit_xml(settings, signed_xml)

        # 5. Guardar resultado en SII batch
        from datetime import datetime

        period = datetime.now().strftime("%Y%m")

        # Insertar en batch
        batch_query = text(
            """
            INSERT INTO sii_batches (tenant_id, period, status)
            VALUES (:tenant_id, :period, 'PENDING')
            ON CONFLICT (tenant_id, period) DO NOTHING
            RETURNING id
        """
        )

        batch_result = db.execute(batch_query, {"tenant_id": tenant_id, "period": period}).first()

        # Si no hay retorno, obtener el batch existente
        if not batch_result:
            existing_batch = db.execute(
                text(
                    """
                SELECT id FROM sii_batches
                WHERE tenant_id = :tenant_id AND period = :period
            """
                ),
                {"tenant_id": tenant_id, "period": period},
            ).first()
            batch_id = existing_batch[0] if existing_batch else None
        else:
            batch_id = batch_result[0]

        # Insertar item en el batch
        if batch_id:
            item_query = text(
                """
                INSERT INTO sii_batch_items (
                    tenant_id, batch_id, invoice_id, status
                ) VALUES (
                    :tenant_id, :batch_id, :invoice_id, :status
                )
            """
            )

            db.execute(
                item_query,
                {
                    "tenant_id": tenant_id,
                    "batch_id": batch_id,
                    "invoice_id": str(invoice_id),
                    "status": result["status"],
                },
            )

        # 6. Actualizar invoice
        if result["status"] == "ACCEPTED":
            update_query = text(
                """
                UPDATE invoices
                SET status = 'posted'
                WHERE id = :invoice_id
            """
            )
            db.execute(update_query, {"invoice_id": invoice_id})

        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"error Facturae {invoice_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="einvoicing.send_einvoice")
def send_einvoice_task(invoice_id: str, tenant_id: str, country: str, env: str = "sandbox"):
    """task unificada: Despachar según país"""

    if country == "EC":
        return sign_and_send_sri_task.delay(invoice_id, tenant_id, env)
    if country == "ES":
        return sign_and_send_facturae_task.delay(invoice_id, tenant_id, env)
    raise ValueError(f"País no soportado: {country}")
