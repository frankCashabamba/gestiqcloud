"""E-Invoicing Service - SII (Agencia Tributaria España) Integration"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.einvoicing.country_settings import EInvoicingCountrySettings
from app.models.einvoicing.einvoice import (
    EInvoice,
    EInvoiceError,
    EInvoiceSignature,
    EInvoiceStatus,
)


class SIIService:
    """Servicio para integración con Agencia Tributaria España (SII)."""

    @staticmethod
    def get_settings(
        db: Session, tenant_id: UUID, country: str = "ES"
    ) -> EInvoicingCountrySettings:
        """Obtiene configuración desde BD (NO HARDCODEADO)."""
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
        """
        Obtiene endpoint API desde BD.

        ✅ NO HARDCODEADO - viene de einvoicing_country_settings.api_endpoint
        """
        settings = SIIService.get_settings(db, tenant_id, country)

        if not settings.api_endpoint:
            raise ValueError(f"API endpoint not configured for {country}")

        return settings.api_endpoint

    @staticmethod
    def validate_invoice_data(invoice_data: dict, country: str = "ES") -> list[str]:
        """
        Valida datos de factura antes de enviar.

        Retorna lista de errores (vacía si válido).
        """
        errors = []

        if country == "ES":
            # Validar CIF
            if not invoice_data.get("company_cif"):
                errors.append("company_cif_required")
            elif len(invoice_data["company_cif"]) < 8:
                errors.append("company_cif_invalid_format")

            # Validar NIF cliente
            if not invoice_data.get("customer_nif"):
                errors.append("customer_nif_required")

            # Validar número de factura único
            if not invoice_data.get("invoice_number"):
                errors.append("invoice_number_required")

            # Validar IVA
            if "total_vat" in invoice_data:
                subtotal = Decimal(str(invoice_data.get("subtotal", 0)))
                vat = Decimal(str(invoice_data.get("total_vat", 0)))
                # IVA debe ser 21%, 10% o 4% de subtotal (aproximadamente)
                valid_rates = [Decimal("0.21"), Decimal("0.10"), Decimal("0.04")]
                calculated_rate = vat / subtotal if subtotal > 0 else Decimal("0")
                if calculated_rate not in valid_rates and calculated_rate > 0:
                    errors.append(f"vat_rate_invalid: {calculated_rate}")

        return errors

    @staticmethod
    def generate_xml(invoice_data: dict, country: str = "ES") -> str:
        """
        Genera XML según formato del país.

        Para España: Facturae 3.2.1 (simplificado)
        """
        root = ET.Element("factura")
        root.set("version", "3.2.1")

        if country == "ES":
            # Header
            header = ET.SubElement(root, "cabecera")

            # Empresa
            empresa = ET.SubElement(header, "empresa")
            ET.SubElement(empresa, "cif").text = invoice_data.get("company_cif", "")
            ET.SubElement(empresa, "nombre_empresa").text = invoice_data.get("company_name", "")

            # Factura info
            factura_info = ET.SubElement(header, "factura_informacion")
            ET.SubElement(factura_info, "numero").text = invoice_data.get("invoice_number", "")
            ET.SubElement(factura_info, "fecha").text = invoice_data.get("issue_date", "")
            ET.SubElement(factura_info, "tipo").text = "E"  # E = Emisión normal

            # Datos cliente
            cliente = ET.SubElement(root, "cliente")
            ET.SubElement(cliente, "nif").text = invoice_data.get("customer_nif", "")
            ET.SubElement(cliente, "nombre").text = invoice_data.get("customer_name", "")
            ET.SubElement(cliente, "direccion").text = invoice_data.get("customer_address", "")

            # Líneas
            lineas = ET.SubElement(root, "lineas")
            for line in invoice_data.get("lines", []):
                linea = ET.SubElement(lineas, "linea")
                ET.SubElement(linea, "descripcion").text = line.get("description", "")
                ET.SubElement(linea, "cantidad").text = str(line.get("quantity", 0))
                ET.SubElement(linea, "precio_unitario").text = str(line.get("unit_price", 0))
                ET.SubElement(linea, "total").text = str(line.get("total", 0))

            # Totales
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
        """
        Envía factura a SII y crea registro EInvoice.

        Returns:
        {
            "status": "PENDING" | "SENT" | "ACCEPTED" | "REJECTED",
            "fiscal_number": "...",
            "authorization_code": "...",
            "error": "..." (si aplica)
        }
        """
        # 1. Validar datos
        validation_errors = SIIService.validate_invoice_data(invoice_data, "ES")
        if validation_errors:
            raise ValueError(f"Validation errors: {validation_errors}")

        # 2. Generar XML
        xml_content = SIIService.generate_xml(invoice_data, "ES")

        # 3. Crear registro EInvoice
        einvoice = EInvoice(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            country="ES",
            xml_content=xml_content,
            status="PENDING",
        )
        db.add(einvoice)
        db.flush()

        # 4. Registrar estado inicial
        status_record = EInvoiceStatus(
            einvoice_id=einvoice.id,
            old_status=None,
            new_status="PENDING",
            reason="Initial creation",
        )
        db.add(status_record)

        # 5. Simular envío a SII (en prod: HTTP POST real)
        # TODO: Implementar POST real a SII endpoint
        try:
            # Obtener settings (endpoint, credenciales)
            SIIService.get_settings(db, tenant_id, "ES")

            # En desarrollo: simular aceptación
            einvoice.status = "SENT"
            einvoice.sent_at = datetime.utcnow()

            # Simular respuesta positiva (en prod: parsear response XML)
            fiscal_number = f"SII{invoice_data.get('invoice_number')}"
            einvoice.fiscal_number = fiscal_number
            einvoice.authorization_code = f"AUTH{einvoice.id}"
            einvoice.authorization_date = datetime.utcnow()
            einvoice.status = "ACCEPTED"
            einvoice.accepted_at = datetime.utcnow()

            # Crear firma (placeholder)
            signature = EInvoiceSignature(
                einvoice_id=einvoice.id,
                status="SIGNED",
                digest_algorithm="SHA256",
            )
            db.add(signature)

            response = {
                "status": "ACCEPTED",
                "fiscal_number": fiscal_number,
                "authorization_code": einvoice.authorization_code,
            }

        except Exception as e:
            einvoice.status = "ERROR"

            error = EInvoiceError(
                einvoice_id=einvoice.id,
                error_message=str(e),
                error_type="SERVER",
                is_recoverable=True,
            )
            db.add(error)

            # Schedule retry
            einvoice.retry_count = 1
            einvoice.next_retry_at = datetime.utcnow() + timedelta(minutes=5)
            einvoice.status = "RETRY"

            response = {
                "status": "ERROR",
                "error": str(e),
            }

        db.flush()
        return response

    @staticmethod
    def retry_send(db: Session, einvoice_id: UUID) -> dict:
        """Reintenta envío de factura."""
        einvoice = db.get(EInvoice, einvoice_id)
        if not einvoice:
            raise ValueError(f"EInvoice {einvoice_id} not found")

        if einvoice.retry_count >= 5:
            raise ValueError("Max retry attempts reached")

        # Simular reintento
        einvoice.retry_count += 1
        einvoice.status = "SENT"
        einvoice.sent_at = datetime.utcnow()

        # En prod: implementar lógica real de reintento
        einvoice.status = "ACCEPTED"
        einvoice.accepted_at = datetime.utcnow()

        db.flush()

        return {
            "status": "ACCEPTED",
            "retry_count": einvoice.retry_count,
        }

    @staticmethod
    def get_status(db: Session, einvoice_id: UUID) -> dict:
        """Obtiene estado de factura electrónica."""
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
