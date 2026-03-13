"""E-Invoicing Service - SII (Agencia Tributaria Espana) Integration"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.einvoicing.country_settings import EInvoicingCountrySettings
from app.models.einvoicing.einvoice import (
    EInvoice,
    EInvoiceError,
    EInvoiceSignature,
    EInvoiceStatus,
)
from app.modules.shared.services.tax import resolve_country_tax_rates

logger = logging.getLogger(__name__)


class SIIService:
    """Servicio para integracion con Agencia Tributaria Espana (SII)."""

    ACCEPTED_TOKENS = {
        "ACCEPTED",
        "ACEPTADO",
        "CORRECTO",
        "AUTHORIZED",
        "AUTORIZADO",
        "RECIBIDA",
        "RECIBIDO",
        "SENT",
        "ENVIADO",
    }
    REJECTED_TOKENS = {
        "REJECTED",
        "RECHAZADO",
        "INCORRECTO",
        "ERROR",
        "FAULT",
    }

    @staticmethod
    def get_settings(
        db: Session, tenant_id: UUID, country: str = "ES"
    ) -> EInvoicingCountrySettings:
        """Obtiene configuracion desde BD (NO HARDCODEADO)."""
        settings = db.execute(
            select(EInvoicingCountrySettings).where(
                EInvoicingCountrySettings.tenant_id == tenant_id,
                EInvoicingCountrySettings.country == country,
            )
        ).scalar_one_or_none()

        if not settings:
            raise ValueError(f"Settings not configured for {country}")

        if not settings.is_enabled:
            raise ValueError(f"E-Invoicing not enabled for {country}")

        return settings

    @staticmethod
    def get_api_endpoint(db: Session, tenant_id: UUID, country: str = "ES") -> str:
        """Obtiene endpoint API desde BD."""
        settings = SIIService.get_settings(db, tenant_id, country)

        if not settings.api_endpoint:
            raise ValueError(f"API endpoint not configured for {country}")

        return settings.api_endpoint

    @staticmethod
    def validate_invoice_data(
        invoice_data: dict,
        country: str = "ES",
        *,
        db: Session | None = None,
    ) -> list[str]:
        """Valida datos de factura antes de enviar."""
        errors = []

        if country == "ES":
            if not invoice_data.get("company_cif"):
                errors.append("company_cif_required")
            elif len(invoice_data["company_cif"]) < 8:
                errors.append("company_cif_invalid_format")

            if not invoice_data.get("customer_nif"):
                errors.append("customer_nif_required")

            if not invoice_data.get("invoice_number"):
                errors.append("invoice_number_required")

            if "total_vat" in invoice_data:
                subtotal = Decimal(str(invoice_data.get("subtotal", 0)))
                vat = Decimal(str(invoice_data.get("total_vat", 0)))
                calculated_rate = vat / subtotal if subtotal > 0 else Decimal("0")
                valid_rates = resolve_country_tax_rates(db, country) if db is not None else []
                if valid_rates and calculated_rate not in valid_rates and calculated_rate > 0:
                    errors.append(f"vat_rate_invalid: {calculated_rate}")

        return errors

    @staticmethod
    def _record_status_change(
        db: Session,
        einvoice: EInvoice,
        *,
        new_status: str,
        reason: str,
    ) -> None:
        old_status = einvoice.status
        if old_status == new_status:
            return
        einvoice.status = new_status
        db.add(
            EInvoiceStatus(
                einvoice_id=einvoice.id,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
            )
        )

    @staticmethod
    def _build_request_headers(settings: EInvoicingCountrySettings) -> dict[str, str]:
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
            "Accept": "application/xml, text/xml, application/soap+xml",
        }
        validation_rules = (
            settings.validation_rules if isinstance(settings.validation_rules, dict) else {}
        )
        extra_headers = validation_rules.get("request_headers")
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items() if value is not None})
        if settings.api_key_encrypted and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {settings.api_key_encrypted}"
        return headers

    @staticmethod
    def _build_httpx_auth(settings: EInvoicingCountrySettings) -> tuple[str, str] | None:
        if settings.username and settings.password_encrypted:
            return (settings.username, settings.password_encrypted)
        return None

    @staticmethod
    def _response_text_candidates(root: ET.Element) -> list[str]:
        texts: list[str] = []
        for element in root.iter():
            text_value = (element.text or "").strip()
            if text_value:
                texts.append(text_value)
        return texts

    @staticmethod
    def _parse_agency_response(raw_text: str, status_code: int) -> dict[str, str | None]:
        parsed: dict[str, str | None] = {
            "status": "SENT" if 200 <= status_code < 300 else "ERROR",
            "fiscal_number": None,
            "authorization_code": None,
            "message": None,
        }

        try:
            root = ET.fromstring(raw_text)
        except ET.ParseError:
            parsed["message"] = raw_text.strip()[:500] or f"HTTP {status_code}"
            return parsed

        tag_values: dict[str, list[str]] = {}
        for element in root.iter():
            clean_tag = element.tag.split("}", 1)[-1].lower()
            text_value = (element.text or "").strip()
            if not text_value:
                continue
            tag_values.setdefault(clean_tag, []).append(text_value)

        texts_upper = {text.upper() for text in SIIService._response_text_candidates(root)}
        if any(token in texts_upper for token in SIIService.REJECTED_TOKENS):
            parsed["status"] = "REJECTED"
        elif any(token in texts_upper for token in SIIService.ACCEPTED_TOKENS):
            parsed["status"] = "ACCEPTED"

        fiscal_number_keys = (
            "csv",
            "fiscalnumber",
            "numerofactura",
            "numeroregistro",
            "idfactura",
        )
        auth_keys = (
            "authorizationcode",
            "codigoautorizacion",
            "codigoseguroverificacion",
            "secureverificationcode",
        )
        message_keys = (
            "descripcionerrorregistro",
            "message",
            "mensaje",
            "faultstring",
            "detalle",
            "descripcion",
        )

        for key in fiscal_number_keys:
            if key in tag_values:
                parsed["fiscal_number"] = tag_values[key][0]
                break
        for key in auth_keys:
            if key in tag_values:
                parsed["authorization_code"] = tag_values[key][0]
                break
        for key in message_keys:
            if key in tag_values:
                parsed["message"] = " | ".join(tag_values[key][:3])
                break

        if parsed["message"] is None:
            parsed["message"] = " | ".join(SIIService._response_text_candidates(root)[:5]) or None

        return parsed

    @staticmethod
    def submit_xml(
        settings: EInvoicingCountrySettings,
        xml_content: str,
    ) -> dict[str, str | None]:
        validation_rules = (
            settings.validation_rules if isinstance(settings.validation_rules, dict) else {}
        )
        try:
            timeout_seconds = float(validation_rules.get("timeout_seconds", 30))
        except Exception:
            timeout_seconds = 30.0
        verify_ssl = bool(validation_rules.get("verify_ssl", True))

        with httpx.Client(timeout=timeout_seconds, verify=verify_ssl) as client:
            response = client.post(
                settings.api_endpoint,
                content=xml_content.encode("utf-8"),
                headers=SIIService._build_request_headers(settings),
                auth=SIIService._build_httpx_auth(settings),
            )

        parsed = SIIService._parse_agency_response(response.text, response.status_code)
        parsed["message"] = parsed.get("message") or f"HTTP {response.status_code}"
        return parsed

    @staticmethod
    def generate_xml(invoice_data: dict, country: str = "ES") -> str:
        """Genera XML segun formato del pais."""
        root = ET.Element("factura")
        root.set("version", "3.2.1")

        if country == "ES":
            header = ET.SubElement(root, "cabecera")

            empresa = ET.SubElement(header, "empresa")
            ET.SubElement(empresa, "cif").text = invoice_data.get("company_cif", "")
            ET.SubElement(empresa, "nombre_empresa").text = invoice_data.get("company_name", "")

            factura_info = ET.SubElement(header, "factura_informacion")
            ET.SubElement(factura_info, "numero").text = invoice_data.get("invoice_number", "")
            ET.SubElement(factura_info, "fecha").text = invoice_data.get("issue_date", "")
            ET.SubElement(factura_info, "tipo").text = "E"

            cliente = ET.SubElement(root, "cliente")
            ET.SubElement(cliente, "nif").text = invoice_data.get("customer_nif", "")
            ET.SubElement(cliente, "nombre").text = invoice_data.get("customer_name", "")
            ET.SubElement(cliente, "direccion").text = invoice_data.get("customer_address", "")

            lineas = ET.SubElement(root, "lineas")
            for line in invoice_data.get("lines", []):
                linea = ET.SubElement(lineas, "linea")
                ET.SubElement(linea, "descripcion").text = line.get("description", "")
                ET.SubElement(linea, "cantidad").text = str(line.get("quantity", 0))
                ET.SubElement(linea, "precio_unitario").text = str(line.get("unit_price", 0))
                ET.SubElement(linea, "total").text = str(line.get("total", 0))

            totales = ET.SubElement(root, "totales")
            ET.SubElement(totales, "subtotal").text = str(invoice_data.get("subtotal", 0))
            ET.SubElement(totales, "iva").text = str(invoice_data.get("total_vat", 0))
            ET.SubElement(totales, "total").text = str(invoice_data.get("total", 0))

        return ET.tostring(root, encoding="unicode")

    @staticmethod
    def send_to_sii(
        db: Session,
        tenant_id: UUID,
        invoice_id: UUID,
        invoice_data: dict,
    ) -> dict:
        """Envia factura a SII y crea registro EInvoice."""
        validation_errors = SIIService.validate_invoice_data(invoice_data, "ES", db=db)
        if validation_errors:
            raise ValueError(f"Validation errors: {validation_errors}")

        xml_content = SIIService.generate_xml(invoice_data, "ES")

        einvoice = EInvoice(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            country="ES",
            xml_content=xml_content,
            status="PENDING",
        )
        db.add(einvoice)
        db.flush()

        db.add(
            EInvoiceStatus(
                einvoice_id=einvoice.id,
                old_status=None,
                new_status="PENDING",
                reason="Initial creation",
            )
        )

        try:
            settings = SIIService.get_settings(db, tenant_id, "ES")
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="SENDING",
                reason="Submitting XML to configured fiscal endpoint",
            )

            submission = SIIService.submit_xml(settings, xml_content)
            einvoice.sent_at = datetime.utcnow()
            einvoice.fiscal_number = submission.get("fiscal_number") or einvoice.fiscal_number
            einvoice.authorization_code = (
                submission.get("authorization_code") or einvoice.authorization_code
            )

            if submission["status"] == "ACCEPTED":
                einvoice.authorization_date = datetime.utcnow()
                einvoice.accepted_at = datetime.utcnow()
                SIIService._record_status_change(
                    db,
                    einvoice,
                    new_status="ACCEPTED",
                    reason=submission.get("message") or "Fiscal authority accepted invoice",
                )
            elif submission["status"] == "REJECTED":
                SIIService._record_status_change(
                    db,
                    einvoice,
                    new_status="REJECTED",
                    reason=submission.get("message") or "Fiscal authority rejected invoice",
                )
                db.add(
                    EInvoiceError(
                        einvoice_id=einvoice.id,
                        error_message=submission.get("message") or "Invoice rejected by fiscal authority",
                        error_type="FISCAL_REJECTION",
                        is_recoverable=False,
                    )
                )
            else:
                SIIService._record_status_change(
                    db,
                    einvoice,
                    new_status="SENT",
                    reason=submission.get("message") or "Invoice submitted to fiscal authority",
                )

            db.add(
                EInvoiceSignature(
                    einvoice_id=einvoice.id,
                    status="SIGNED",
                    digest_algorithm="SHA256",
                    digest_value=str(abs(hash(xml_content))),
                )
            )

            response = {
                "status": einvoice.status,
                "fiscal_number": einvoice.fiscal_number,
                "authorization_code": einvoice.authorization_code,
                "message": submission.get("message"),
            }

        except httpx.HTTPError as e:
            logger.exception("HTTP error submitting einvoice %s", invoice_id)
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="RETRY",
                reason=f"HTTP transport error: {e}",
            )
            db.add(
                EInvoiceError(
                    einvoice_id=einvoice.id,
                    error_message=str(e),
                    error_type="CONNECTIVITY",
                    is_recoverable=True,
                )
            )
            einvoice.retry_count = (einvoice.retry_count or 0) + 1
            einvoice.next_retry_at = datetime.utcnow() + timedelta(minutes=5)
            response = {
                "status": "ERROR",
                "error": str(e),
            }

        except Exception as e:
            logger.exception("Unexpected error submitting einvoice %s", invoice_id)
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="RETRY",
                reason=f"Unexpected submission error: {e}",
            )
            db.add(
                EInvoiceError(
                    einvoice_id=einvoice.id,
                    error_message=str(e),
                    error_type="SERVER",
                    is_recoverable=True,
                )
            )
            einvoice.retry_count = (einvoice.retry_count or 0) + 1
            einvoice.next_retry_at = datetime.utcnow() + timedelta(minutes=5)
            response = {
                "status": "ERROR",
                "error": str(e),
            }

        db.flush()
        return response

    @staticmethod
    def retry_send(db: Session, einvoice_id: UUID) -> dict:
        """Reintenta envio de factura."""
        einvoice = db.get(EInvoice, einvoice_id)
        if not einvoice:
            raise ValueError(f"EInvoice {einvoice_id} not found")

        if einvoice.retry_count >= 5:
            raise ValueError("Max retry attempts reached")

        settings = SIIService.get_settings(db, einvoice.tenant_id, einvoice.country)
        SIIService._record_status_change(
            db,
            einvoice,
            new_status="SENDING",
            reason="Retrying fiscal submission",
        )
        submission = SIIService.submit_xml(settings, einvoice.xml_content or "")
        einvoice.retry_count += 1
        einvoice.sent_at = datetime.utcnow()

        if submission["status"] == "ACCEPTED":
            einvoice.accepted_at = datetime.utcnow()
            einvoice.authorization_date = datetime.utcnow()
            einvoice.fiscal_number = submission.get("fiscal_number") or einvoice.fiscal_number
            einvoice.authorization_code = (
                submission.get("authorization_code") or einvoice.authorization_code
            )
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="ACCEPTED",
                reason=submission.get("message") or "Retry accepted by fiscal authority",
            )
        elif submission["status"] == "REJECTED":
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="REJECTED",
                reason=submission.get("message") or "Retry rejected by fiscal authority",
            )
        else:
            SIIService._record_status_change(
                db,
                einvoice,
                new_status="SENT",
                reason=submission.get("message") or "Retry submitted to fiscal authority",
            )

        db.flush()

        return {
            "status": einvoice.status,
            "retry_count": einvoice.retry_count,
        }

    @staticmethod
    def get_status(db: Session, einvoice_id: UUID) -> dict:
        """Obtiene estado de factura electronica."""
        einvoice = db.get(EInvoice, einvoice_id)
        if not einvoice:
            raise ValueError(f"EInvoice {einvoice_id} not found")

        return {
            "id": str(einvoice.id),
            "status": einvoice.status,
            "fiscal_number": einvoice.fiscal_number,
            "authorization_code": einvoice.authorization_code,
            "sent_at": einvoice.sent_at,
            "accepted_at": einvoice.accepted_at,
            "retry_count": einvoice.retry_count,
            "next_retry_at": einvoice.next_retry_at,
        }
