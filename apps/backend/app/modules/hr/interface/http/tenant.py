"""HR Module - HTTP API (Tenant)"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.hr.payroll import Payroll, PayrollDetail
from app.models.hr.payslip import PaymentSlip
from app.modules.hr.application.payroll_service import PayrollService

router = APIRouter(
    prefix="/hr",
    tags=["HR"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# SCHEMAS
# ============================================================================


class PayrollDetailResponse(BaseModel):
    """Detalle de empleado en nómina."""

    employee_id: UUID
    gross_salary: Decimal
    irpf: Decimal
    social_security: Decimal
    mutual_insurance: Decimal
    total_deductions: Decimal
    net_salary: Decimal

    class Config:
        from_attributes = True


class PayrollResponse(BaseModel):
    """Respuesta de nómina."""

    id: UUID
    payroll_month: str
    payroll_date: date
    status: str
    total_employees: int
    total_gross: Decimal
    total_irpf: Decimal
    total_social_security_employee: Decimal
    total_social_security_employer: Decimal
    total_deductions: Decimal
    total_net: Decimal
    details: list[PayrollDetailResponse] | None = None

    class Config:
        from_attributes = True


class PayrollCreateRequest(BaseModel):
    """Solicitud para generar nómina."""

    payroll_month: str  # "2026-02"
    payroll_date: date


class PaymentSlipResponse(BaseModel):
    """Respuesta de boleta de pago."""

    id: UUID
    employee_id: UUID
    status: str
    sent_at: date | None = None
    viewed_at: date | None = None
    valid_until: date
    download_count: int

    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/payroll/generate", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED
)
async def generate_payroll(
    request: PayrollCreateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """
    Genera nómina para el mes.

    Body:
    {
        "payroll_month": "2026-02",
        "payroll_date": "2026-02-28"
    }
    """
    tenant_id = claims["tenant_id"]

    try:
        payroll = PayrollService.generate_payroll(
            db, tenant_id, request.payroll_month, request.payroll_date
        )

        db.commit()
        db.refresh(payroll)

        return PayrollResponse(
            id=payroll.id,
            payroll_month=payroll.payroll_month,
            payroll_date=payroll.payroll_date,
            status=payroll.status,
            total_employees=payroll.total_employees,
            total_gross=payroll.total_gross,
            total_irpf=payroll.total_irpf,
            total_social_security_employee=payroll.total_social_security_employee,
            total_social_security_employer=payroll.total_social_security_employer,
            total_deductions=payroll.total_deductions,
            total_net=payroll.total_net,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/payroll/{payroll_id}", response_model=PayrollResponse)
async def get_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Obtiene detalle completo de nómina."""
    tenant_id = claims["tenant_id"]

    payroll = db.get(Payroll, payroll_id)
    if not payroll or payroll.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    # Cargar detalles
    details = db.query(PayrollDetail).filter_by(payroll_id=payroll_id).all()

    return PayrollResponse(
        id=payroll.id,
        payroll_month=payroll.payroll_month,
        payroll_date=payroll.payroll_date,
        status=payroll.status,
        total_employees=payroll.total_employees,
        total_gross=payroll.total_gross,
        total_irpf=payroll.total_irpf,
        total_social_security_employee=payroll.total_social_security_employee,
        total_social_security_employer=payroll.total_social_security_employer,
        total_deductions=payroll.total_deductions,
        total_net=payroll.total_net,
        details=[
            PayrollDetailResponse(
                employee_id=d.employee_id,
                gross_salary=d.gross_salary,
                irpf=d.irpf,
                social_security=d.social_security,
                mutual_insurance=d.mutual_insurance,
                total_deductions=d.total_deductions,
                net_salary=d.net_salary,
            )
            for d in details
        ],
    )


@router.post("/payroll/{payroll_id}/confirm", response_model=PayrollResponse)
async def confirm_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Confirma nómina (DRAFT → CONFIRMED)."""
    tenant_id = claims["tenant_id"]
    user_id = claims.get("user_id")

    payroll = db.get(Payroll, payroll_id)
    if not payroll or payroll.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    try:
        payroll = PayrollService.confirm_payroll(db, payroll_id, user_id)
        db.commit()

        return PayrollResponse(
            id=payroll.id,
            payroll_month=payroll.payroll_month,
            payroll_date=payroll.payroll_date,
            status=payroll.status,
            total_employees=payroll.total_employees,
            total_gross=payroll.total_gross,
            total_irpf=payroll.total_irpf,
            total_social_security_employee=payroll.total_social_security_employee,
            total_social_security_employer=payroll.total_social_security_employer,
            total_deductions=payroll.total_deductions,
            total_net=payroll.total_net,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/payroll/{payroll_id}/mark-paid", response_model=PayrollResponse)
async def mark_payroll_paid(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Marca nómina como pagada (CONFIRMED → PAID)."""
    tenant_id = claims["tenant_id"]

    payroll = db.get(Payroll, payroll_id)
    if not payroll or payroll.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    try:
        payroll = PayrollService.mark_payroll_paid(db, payroll_id)
        db.commit()

        return PayrollResponse(
            id=payroll.id,
            payroll_month=payroll.payroll_month,
            payroll_date=payroll.payroll_date,
            status=payroll.status,
            total_employees=payroll.total_employees,
            total_gross=payroll.total_gross,
            total_irpf=payroll.total_irpf,
            total_social_security_employee=payroll.total_social_security_employee,
            total_social_security_employer=payroll.total_social_security_employer,
            total_deductions=payroll.total_deductions,
            total_net=payroll.total_net,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/payroll/{payroll_detail_id}/payslip", response_model=PaymentSlipResponse)
async def get_payslip(
    payroll_detail_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PaymentSlipResponse:
    """Obtiene información de boleta de pago."""
    tenant_id = claims["tenant_id"]

    payslip = (
        db.query(PaymentSlip)
        .filter_by(
            payroll_detail_id=payroll_detail_id,
            tenant_id=tenant_id,
        )
        .first()
    )

    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment slip not found",
        )

    return PaymentSlipResponse(
        id=payslip.id,
        employee_id=payslip.employee_id,
        status=payslip.status,
        sent_at=payslip.sent_at,
        viewed_at=payslip.viewed_at,
        valid_until=payslip.valid_until,
        download_count=payslip.download_count,
    )


@router.get("/payroll/{payroll_detail_id}/payslip/download")
async def download_payslip(
    payroll_detail_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Descarga PDF de boleta."""
    tenant_id = claims["tenant_id"]

    payslip = (
        db.query(PaymentSlip)
        .filter_by(
            payroll_detail_id=payroll_detail_id,
            tenant_id=tenant_id,
        )
        .first()
    )

    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment slip not found",
        )

    if not payslip.pdf_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF not yet generated",
        )

    # Registrar descarga
    payslip.download_count += 1
    from datetime import datetime

    payslip.last_download_at = datetime.utcnow()
    if not payslip.viewed_at:
        payslip.viewed_at = datetime.utcnow()
    db.commit()

    return {
        "filename": f"payslip_{payroll_detail_id}.pdf",
        "content_type": "application/pdf",
        "size": len(payslip.pdf_content),
    }
