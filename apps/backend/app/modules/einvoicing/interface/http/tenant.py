"""E-Invoicing Module - HTTP API (Tenant)"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.einvoicing import SRISubmission
from app.models.core.facturacion import Invoice
from app.modules.einvoicing.application.facturae_xml import generate_facturae_xml
from app.modules.einvoicing.application.sii_service import SIIService
from app.modules.einvoicing.application.sri_service import SRIService

router = APIRouter(
    prefix="/einvoicing",
    tags=["E-Invoicing"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# SCHEMAS
# ============================================================================


class InvoiceLineRequest(BaseModel):
    """Línea de factura."""

    description: str
    quantity: float
    unit_price: float
    total: float


class SendInvoiceRequest(BaseModel):
    """Solicitud para enviar factura a SII."""

    invoice_id: UUID
    company_cif: str
    company_name: str
    customer_nif: str
    customer_name: str
    customer_address: str | None = None
    invoice_number: str
    issue_date: str
    subtotal: float
    total_vat: float
    total: float
    lines: list[InvoiceLineRequest]


class EInvoiceStatusResponse(BaseModel):
    """Estado de factura electrónica."""

    id: UUID
    status: str
    fiscal_number: str | None = None
    authorization_code: str | None = None
    sent_at: str | None = None
    accepted_at: str | None = None
    retry_count: int
    next_retry_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SendInvoiceResponse(BaseModel):
    """Respuesta de envío a SII."""

    einvoice_id: UUID
    status: str
    fiscal_number: str | None = None
    authorization_code: str | None = None
    error: str | None = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/facturae/{invoice_id}/export")
async def export_facturae_xml(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    invoice = db.get(Invoice, invoice_id)
    if not invoice or str(invoice.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    tenant = invoice.tenant
    customer = invoice.customer
    issue_date = invoice.issue_date
    if isinstance(issue_date, str):
        try:
            issue_date = date.fromisoformat(issue_date[:10])
        except Exception:
            issue_date = datetime.now(UTC).date()
    elif issue_date is None:
        issue_date = datetime.now(UTC).date()

    invoice_data = {
        "numero": invoice.numero,
        "fecha": issue_date,
        "subtotal": Decimal(str(invoice.subtotal or 0)),
        "iva": Decimal(str(invoice.iva or 0)),
        "total": Decimal(str(invoice.total or 0)),
        "tax_rate": (
            Decimal(str((invoice.iva or 0) / (invoice.subtotal or 1)))
            if (invoice.subtotal or 0)
            else Decimal("0")
        ),
        "empresa": {
            "nombre": getattr(tenant, "name", "") or "",
            "ruc": getattr(tenant, "tax_id", "") or "",
            "direccion": getattr(tenant, "address", "") or "",
        },
        "cliente": {
            "nombre": getattr(customer, "name", "") or "",
            "ruc": getattr(customer, "tax_id", "") or "",
            "email": getattr(customer, "email", "") or "",
        },
        "lineas": [
            {
                "description": getattr(line, "description", "") or "",
                "quantity": float(getattr(line, "quantity", 0) or 0),
                "unit_price": float(getattr(line, "unit_price", 0) or 0),
                "iva": float(getattr(line, "vat", 0) or 0),
            }
            for line in (invoice.lines or [])
        ],
    }
    xml_content = generate_facturae_xml(invoice_data)
    filename = f"factura-{invoice.numero or invoice.id}.xml"
    return Response(
        content=xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/send-sii", response_model=SendInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def send_invoice_to_sii(
    request: SendInvoiceRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> SendInvoiceResponse:
    """
    Envía factura a Agencia Tributaria (SII - España).

    Body:
    {
        "invoice_id": "uuid",
        "company_cif": "ES12345678A",
        "company_name": "Mi Empresa S.L.",
        "customer_nif": "12345678Z",
        "customer_name": "Cliente",
        "invoice_number": "FAC-2026-001",
        "issue_date": "2026-02-15",
        "subtotal": 1000.00,
        "total_vat": 210.00,
        "total": 1210.00,
        "lines": [...]
    }
    """
    tenant_id = claims["tenant_id"]

    try:
        # Convertir request a dict
        invoice_data = {
            "company_cif": request.company_cif,
            "company_name": request.company_name,
            "customer_nif": request.customer_nif,
            "customer_name": request.customer_name,
            "customer_address": request.customer_address or "",
            "invoice_number": request.invoice_number,
            "issue_date": request.issue_date,
            "subtotal": request.subtotal,
            "total_vat": request.total_vat,
            "total": request.total,
            "lines": [line.dict() for line in request.lines],
        }

        # Enviar a SII
        result = SIIService.send_to_sii(db, tenant_id, request.invoice_id, invoice_data)

        # Obtener einvoice creado
        from sqlalchemy import select

        from app.models.einvoicing.einvoice import EInvoice

        einvoice = db.execute(
            select(EInvoice).where(EInvoice.invoice_id == request.invoice_id)
        ).scalar_one()

        db.commit()

        return SendInvoiceResponse(
            einvoice_id=einvoice.id,
            status=result.get("status"),
            fiscal_number=result.get("fiscal_number"),
            authorization_code=result.get("authorization_code"),
            error=result.get("error"),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/einvoice/{einvoice_id}/status", response_model=EInvoiceStatusResponse)
async def get_einvoice_status(
    einvoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> EInvoiceStatusResponse:
    """Obtiene estado de factura electrónica."""
    tenant_id = claims["tenant_id"]

    from app.models.einvoicing.einvoice import EInvoice

    einvoice = db.get(EInvoice, einvoice_id)
    if not einvoice or einvoice.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EInvoice not found",
        )

    status_info = SIIService.get_status(db, einvoice_id)

    return EInvoiceStatusResponse(
        id=einvoice_id,
        status=status_info.get("status"),
        fiscal_number=status_info.get("fiscal_number"),
        authorization_code=status_info.get("authorization_code"),
        sent_at=status_info.get("sent_at"),
        accepted_at=status_info.get("accepted_at"),
        retry_count=status_info.get("retry_count", 0),
        next_retry_at=status_info.get("next_retry_at"),
    )


# ============================================================================
# SRI Ecuador — Endpoints
# ============================================================================


class SRIStatusResponse(BaseModel):
    """Estado de envío SRI Ecuador."""

    submission_id: UUID
    invoice_id: UUID
    status: str
    clave_acceso: str | None = None
    authorization_number: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SendSRIRequest(BaseModel):
    """Solicitud para enviar invoice al SRI Ecuador."""

    invoice_id: UUID
    env: str = "sandbox"


@router.post("/sri/send", status_code=status.HTTP_202_ACCEPTED)
async def send_invoice_to_sri(
    request: SendSRIRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict:
    """
    Encola la firma y envío del invoice al SRI Ecuador.
    Retorna inmediatamente con el task_id de Celery.

    Body: { "invoice_id": "uuid", "env": "sandbox"|"production" }
    """
    tenant_id = claims["tenant_id"]

    invoice = db.get(Invoice, request.invoice_id)
    if not invoice or str(invoice.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Validar que tiene configuración SRI
    try:
        from uuid import UUID as _UUID

        SRIService.get_settings(db, _UUID(str(tenant_id)), "EC")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    try:
        from app.workers.einvoicing_tasks import sign_and_send_sri_task

        task = sign_and_send_sri_task.delay(str(request.invoice_id), str(tenant_id), request.env)
        return {"task_id": task.id, "status": "queued", "invoice_id": str(request.invoice_id)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/sri/{invoice_id}/status", response_model=SRIStatusResponse)
async def get_sri_status(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> SRIStatusResponse:
    """
    Obtiene el estado de la última submission SRI para el invoice indicado.
    Incluye clave_acceso y número de autorización si ya fue autorizado.
    """
    tenant_id = claims["tenant_id"]

    submission = db.execute(
        select(SRISubmission)
        .where(
            SRISubmission.invoice_id == invoice_id,
            SRISubmission.tenant_id == tenant_id,
        )
        .order_by(SRISubmission.created_at.desc())
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SRI submission found for this invoice",
        )

    return SRIStatusResponse(
        submission_id=submission.id,
        invoice_id=submission.invoice_id,
        status=submission.status,
        clave_acceso=submission.receipt_number,
        authorization_number=submission.authorization_number,
        error_message=submission.error_message,
        created_at=submission.created_at,
    )


@router.get("/sri/{invoice_id}/ride")
async def download_ride_xml(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> Response:
    """
    Descargar el RIDE XML autorizado del SRI.
    Solo disponible cuando status = AUTHORIZED.
    """
    tenant_id = claims["tenant_id"]

    submission = db.execute(
        select(SRISubmission)
        .where(
            SRISubmission.invoice_id == invoice_id,
            SRISubmission.tenant_id == tenant_id,
            SRISubmission.status == "AUTHORIZED",
        )
        .order_by(SRISubmission.created_at.desc())
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RIDE no disponible: el comprobante no ha sido autorizado aún",
        )

    # Usar el XML autorizado si lo tenemos (response), si no el payload firmado
    xml_content = submission.response or submission.payload
    if not xml_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="XML del comprobante no disponible",
        )

    filename = f"RIDE-{submission.receipt_number or invoice_id}.xml"
    return Response(
        content=xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/einvoice/{einvoice_id}/retry", response_model=SendInvoiceResponse)
async def retry_einvoice(
    einvoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> SendInvoiceResponse:
    """Reintenta envío de factura a SII."""
    tenant_id = claims["tenant_id"]

    from app.models.einvoicing.einvoice import EInvoice

    einvoice = db.get(EInvoice, einvoice_id)
    if not einvoice or einvoice.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EInvoice not found",
        )

    try:
        result = SIIService.retry_send(db, einvoice_id)
        db.commit()
        db.refresh(einvoice)

        return SendInvoiceResponse(
            einvoice_id=einvoice_id,
            status=result.get("status"),
            fiscal_number=einvoice.fiscal_number,
            authorization_code=einvoice.authorization_code,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
