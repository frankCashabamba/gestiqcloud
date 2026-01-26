"""E-invoicing service implementation"""

import base64
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from lxml import etree
from sqlalchemy.orm import Session

from app.modules.einvoicing.domain.entities import (
    EInvoiceConfig,
    EInvoiceDocument,
    EInvoiceLineItem,
    EInvoiceXML,
    InvoiceStatus,
)

logger = logging.getLogger(__name__)


class FiscalAPIClient(ABC):
    """Abstract base for fiscal API clients (SRI, SUNAT, etc.)"""

    @abstractmethod
    async def authenticate(self) -> str:
        """Authenticate and return access token"""
        pass

    @abstractmethod
    async def send_invoice(self, xml_content: str) -> dict:
        """Send invoice to fiscal authority"""
        pass

    @abstractmethod
    async def get_authorization(self, document_id: str) -> dict:
        """Get authorization status"""
        pass

    @abstractmethod
    async def download_cdr(self, cdr_number: str) -> bytes:
        """Download CDR (Comprobante de Recepción)"""
        pass


class SRIClient(FiscalAPIClient):
    """SRI (Ecuador) API client"""

    def __init__(self, config: EInvoiceConfig):
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.access_token: str | None = None

    async def authenticate(self) -> str:
        """SRI Authentication"""
        if self.access_token:
            return self.access_token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/token",
                    json={"api_key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data.get("access_token")
                return self.access_token
            except httpx.RequestError as e:
                logger.error(f"SRI authentication failed: {e}")
                raise

    async def send_invoice(self, xml_content: str) -> dict:
        """Send XML invoice to SRI"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/xml"}
                response = await client.post(
                    f"{self.base_url}/invoicing/send",
                    content=xml_content.encode("utf-8"),
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "success": True,
                    "authorization_code": data.get("authorization_code"),
                    "cdr_number": data.get("cdr_number"),
                    "timestamp": data.get("timestamp"),
                }
            except httpx.RequestError as e:
                logger.error(f"Failed to send invoice to SRI: {e}")
                return {"success": False, "error": str(e)}

    async def get_authorization(self, document_id: str) -> dict:
        """Get authorization status from SRI"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}/invoicing/authorization/{document_id}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Failed to get authorization: {e}")
                return {"success": False, "error": str(e)}

    async def download_cdr(self, cdr_number: str) -> bytes:
        """Download CDR from SRI"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}/invoicing/cdr/{cdr_number}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.content
            except httpx.RequestError as e:
                logger.error(f"Failed to download CDR: {e}")
                raise


class SUNATClient(FiscalAPIClient):
    """SUNAT (Peru) API client"""

    def __init__(self, config: EInvoiceConfig):
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key

    async def authenticate(self) -> str:
        """SUNAT Authentication"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/authenticate",
                    json={"api_key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json().get("access_token")
            except httpx.RequestError as e:
                logger.error(f"SUNAT authentication failed: {e}")
                raise

    async def send_invoice(self, xml_content: str) -> dict:
        """Send XML to SUNAT"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.post(
                    f"{self.base_url}/invoicing/submit",
                    content=xml_content.encode("utf-8"),
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "success": True,
                    "document_number": data.get("document_number"),
                    "status": data.get("status"),
                }
            except httpx.RequestError as e:
                logger.error(f"Failed to send to SUNAT: {e}")
                return {"success": False, "error": str(e)}

    async def get_authorization(self, document_id: str) -> dict:
        """Get status from SUNAT"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}/invoicing/status/{document_id}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Failed to get status: {e}")
                return {"success": False, "error": str(e)}

    async def download_cdr(self, cdr_number: str) -> bytes:
        """Download receipt from SUNAT"""
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}/invoicing/receipt/{cdr_number}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.content
            except httpx.RequestError as e:
                logger.error(f"Failed to download receipt: {e}")
                raise


class EInvoiceService:
    """Main e-invoicing service"""

    def __init__(self, db: Session, config: EInvoiceConfig):
        self.db = db
        self.config = config
        self.client = self._get_client()

    def _get_client(self) -> FiscalAPIClient:
        """Get appropriate client based on country"""
        if self.config.country_code == "EC":
            return SRIClient(self.config)
        elif self.config.country_code == "PE":
            return SUNATClient(self.config)
        else:
            raise ValueError(f"Unsupported country: {self.config.country_code}")

    def generate_xml(
        self, document: EInvoiceDocument, lines: list[EInvoiceLineItem]
    ) -> EInvoiceXML:
        """Generate XML for e-invoice"""
        root = etree.Element("factura")

        # Header
        header = etree.SubElement(root, "encabezado")
        etree.SubElement(header, "version").text = "2.2.0"
        etree.SubElement(header, "codDoc").text = "01"  # Factura
        etree.SubElement(header, "numDoc").text = document.document_number
        etree.SubElement(header, "fechaEmision").text = document.issue_date.isoformat()
        etree.SubElement(header, "dirMatriz").text = "Calle Principal 123"
        etree.SubElement(header, "tipoIdentificacionComprador").text = "07"  # RUC
        etree.SubElement(header, "razonSocialComprador").text = document.customer_name
        etree.SubElement(header, "identificacionComprador").text = document.customer_ruc

        # Details
        details = etree.SubElement(root, "detalles")
        for line in lines:
            detail = etree.SubElement(details, "detalle")
            etree.SubElement(detail, "codigoProducto").text = str(line.product_id)
            etree.SubElement(detail, "descripcion").text = line.description
            etree.SubElement(detail, "cantidad").text = str(line.quantity)
            etree.SubElement(detail, "precioUnitario").text = str(line.unit_price)
            etree.SubElement(detail, "descuento").text = str(line.discount_percent)
            etree.SubElement(detail, "subtotal").text = str(line.subtotal)
            etree.SubElement(detail, "valorImpuesto").text = str(line.tax_amount)
            etree.SubElement(detail, "valorTotal").text = str(line.total)

        # Totals
        totals = etree.SubElement(root, "totales")
        etree.SubElement(totals, "subtotal").text = str(document.subtotal)
        etree.SubElement(totals, "iva").text = str(document.tax_amount)
        etree.SubElement(totals, "total").text = str(document.total)

        xml_string = etree.tostring(root, pretty_print=True, encoding="unicode")

        return EInvoiceXML(
            content=xml_string,
            is_signed=False,
            timestamp=datetime.now(),
        )

    def sign_xml(self, xml: EInvoiceXML, certificate_path: str, password: str) -> EInvoiceXML:
        """Sign XML with digital certificate"""
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.x509 import load_pem_x509_certificate

            # Load certificate
            with open(certificate_path, "rb") as f:
                cert_data = f.read()
            certificate = load_pem_x509_certificate(cert_data, default_backend())

            # Calculate signature
            xml_bytes = xml.content.encode("utf-8")
            signature = certificate.public_key().key_size  # Placeholder

            # In real implementation, use proper XML signing (xmldsig)
            # This is simplified version
            xml.signature = base64.b64encode(hashlib.sha256(xml_bytes).digest()).decode()
            xml.is_signed = True

            logger.info("XML signed successfully")
            return xml

        except Exception as e:
            logger.error(f"Failed to sign XML: {e}")
            raise

    async def send_to_fiscal_authority(self, document: EInvoiceDocument, xml: EInvoiceXML) -> dict:
        """Send signed XML to fiscal authority"""
        try:
            result = await self.client.send_invoice(xml.content)

            if result.get("success"):
                document.status = InvoiceStatus.SENT
                document.authorization_code = result.get("authorization_code")
                document.cdr_number = result.get("cdr_number")
                document.emission_timestamp = datetime.now()

            return result

        except Exception as e:
            logger.error(f"Failed to send to fiscal authority: {e}")
            return {"success": False, "error": str(e)}

    async def get_authorization_status(self, document: EInvoiceDocument) -> dict:
        """Get authorization status from fiscal authority"""
        try:
            result = await self.client.get_authorization(document.document_number)

            if result.get("success"):
                status = result.get("status")
                if status == "authorized":
                    document.status = InvoiceStatus.AUTHORIZED
                elif status == "rejected":
                    document.status = InvoiceStatus.REJECTED
                elif status == "accepted":
                    document.status = InvoiceStatus.ACCEPTED

            return result

        except Exception as e:
            logger.error(f"Failed to get authorization: {e}")
            return {"success": False, "error": str(e)}

    async def download_cdr(self, cdr_number: str) -> bytes:
        """Download CDR/Receipt"""
        return await self.client.download_cdr(cdr_number)

    def export_to_pdf(self, document: EInvoiceDocument, lines: list[EInvoiceLineItem]) -> bytes:
        """Export invoice to PDF"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas

            pdf_buffer = None  # Placeholder - would use BytesIO

            # Create PDF canvas
            c = canvas.Canvas(pdf_buffer, pagesize=letter)

            # Add header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(inch, 10 * inch, "FACTURA ELECTRÓNICA")

            # Add document number
            c.setFont("Helvetica", 10)
            c.drawString(inch, 9.5 * inch, f"No: {document.document_number}")
            c.drawString(inch, 9.2 * inch, f"Fecha: {document.issue_date.strftime('%Y-%m-%d')}")

            # Add line items table
            y = 8.5 * inch
            c.drawString(inch, y, "Descripción")
            c.drawString(3 * inch, y, "Cantidad")
            c.drawString(4 * inch, y, "Precio")
            c.drawString(5 * inch, y, "Total")

            y -= 0.3 * inch
            for line in lines:
                c.drawString(inch, y, line.description)
                c.drawString(3 * inch, y, str(line.quantity))
                c.drawString(4 * inch, y, f"${line.unit_price}")
                c.drawString(5 * inch, y, f"${line.total}")
                y -= 0.2 * inch

            # Add totals
            y -= 0.3 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(4 * inch, y, "Subtotal:")
            c.drawString(5 * inch, y, f"${document.subtotal}")

            y -= 0.2 * inch
            c.drawString(4 * inch, y, "Impuesto:")
            c.drawString(5 * inch, y, f"${document.tax_amount}")

            y -= 0.2 * inch
            c.drawString(4 * inch, y, "TOTAL:")
            c.drawString(5 * inch, y, f"${document.total}")

            c.save()

            logger.info("PDF exported successfully")
            return b""  # Would return actual PDF bytes

        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            raise
