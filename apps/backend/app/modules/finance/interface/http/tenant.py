"""Finance Module - HTTP API (Tenant)"""

from datetime import date, datetime, UTC
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.finance.banco import BankMovement
from app.models.finance.cash_management import CashMovement
from app.modules.finance.application.cash_service import CashPositionService

router = APIRouter(
    prefix="/finance",
    tags=["Finance"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# SCHEMAS
# ============================================================================


class CashPositionResponse(BaseModel):
    """Respuesta de posición de caja."""

    date: date
    bank_account_id: UUID
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    closing_balance: Decimal
    currency: str

    class Config:
        from_attributes = True


class CashProjectionResponse(BaseModel):
    """Respuesta de proyección de flujo de caja."""

    projection_date: date
    projection_end_date: date
    period_days: int
    opening_balance: Decimal
    projected_inflows: Decimal
    projected_outflows: Decimal
    projected_balance: Decimal
    scenario: str

    class Config:
        from_attributes = True


class MultiDayPositionResponse(BaseModel):
    """Respuesta multi-día."""

    start_date: date
    end_date: date
    positions: list[CashPositionResponse]
    total_inflows: Decimal
    total_outflows: Decimal


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/cash-position")
async def get_cash_position(
    bank_account_id: UUID,
    position_date: date | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> CashPositionResponse:
    """
    Obtiene posición de caja para una fecha.

    Query params:
    - bank_account_id: UUID de cuenta bancaria (ChartOfAccounts)
    - position_date: fecha (default: hoy)
    """
    tenant_id = claims["tenant_id"]

    if not position_date:
        position_date = date.today()

    try:
        position = CashPositionService.calculate_position(
            db, tenant_id, bank_account_id, position_date
        )

        return CashPositionResponse(
            date=position.position_date,
            bank_account_id=position.bank_account_id,
            opening_balance=position.opening_balance,
            inflows=position.inflows,
            outflows=position.outflows,
            closing_balance=position.closing_balance,
            currency=position.currency,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/cash-position/range")
async def get_cash_positions_range(
    bank_account_id: UUID,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> MultiDayPositionResponse:
    """
    Obtiene posiciones de caja para un rango de fechas.

    Query params:
    - bank_account_id: UUID de cuenta bancaria
    - start_date: fecha inicio
    - end_date: fecha fin
    """
    tenant_id = claims["tenant_id"]

    try:
        positions = CashPositionService.get_multi_day_positions(
            db, tenant_id, bank_account_id, start_date, end_date
        )

        total_inflows = sum(p.inflows for p in positions)
        total_outflows = sum(p.outflows for p in positions)

        return MultiDayPositionResponse(
            start_date=start_date,
            end_date=end_date,
            positions=[
                CashPositionResponse(
                    date=p.position_date,
                    bank_account_id=p.bank_account_id,
                    opening_balance=p.opening_balance,
                    inflows=p.inflows,
                    outflows=p.outflows,
                    closing_balance=p.closing_balance,
                    currency=p.currency,
                )
                for p in positions
            ],
            total_inflows=total_inflows,
            total_outflows=total_outflows,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/cash-forecast")
async def get_cash_forecast(
    bank_account_id: UUID,
    days: int = Query(30, ge=7, le=365),
    scenario: str = "BASE",
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> CashProjectionResponse:
    """
    Obtiene pronóstico de flujo de caja.

    Query params:
    - bank_account_id: UUID de cuenta
    - days: número de días a proyectar (default: 30)
    - scenario: OPTIMISTIC, BASE, PESSIMISTIC
    """
    tenant_id = claims["tenant_id"]

    try:
        projection = CashPositionService.create_projection(db, tenant_id, bank_account_id, days)

        return CashProjectionResponse(
            projection_date=projection.projection_date,
            projection_end_date=projection.projection_end_date,
            period_days=projection.period_days,
            opening_balance=projection.opening_balance,
            projected_inflows=projection.projected_inflows,
            projected_outflows=projection.projected_outflows,
            projected_balance=projection.projected_balance,
            scenario=projection.scenario,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# CASHBOX MOVEMENTS  (GET /finance/cashbox/movements)
# ============================================================================


class MovimientoOut(BaseModel):
    id: str
    fecha: str
    concepto: str
    tipo: str  # "ingreso" | "egreso"
    monto: float
    referencia: str | None = None
    cuenta: str | None = None
    conciliado: bool = True
    created_at: str | None = None


@router.get("/cashbox/movements", response_model=list[MovimientoOut])
def list_cashbox_movements(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[MovimientoOut]:
    """Lista movimientos de caja del tenant."""
    tenant_id = claims["tenant_id"]
    offset = (page - 1) * page_size

    rows = (
        db.execute(
            select(CashMovement)
            .where(CashMovement.tenant_id == tenant_id)
            .order_by(CashMovement.date.desc(), CashMovement.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return [
        MovimientoOut(
            id=str(r.id),
            fecha=r.date.isoformat(),
            concepto=r.description,
            tipo="ingreso" if r.type == "INCOME" else "egreso",
            monto=float(r.amount),
            referencia=str(r.ref_doc_id) if r.ref_doc_id else None,
            cuenta=str(r.cash_box_id) if r.cash_box_id else None,
            conciliado=True,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


# ============================================================================
# BANK MOVEMENTS  (GET /finance/bank/movements)
# ============================================================================


class MovimientoBancoOut(MovimientoOut):
    banco: str = ""
    numero_cuenta: str = ""


@router.get("/bank/movements", response_model=list[MovimientoBancoOut])
def list_bank_movements(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[MovimientoBancoOut]:
    """Lista movimientos bancarios del tenant."""
    tenant_id = claims["tenant_id"]
    offset = (page - 1) * page_size

    rows = (
        db.execute(
            select(BankMovement)
            .where(BankMovement.tenant_id == tenant_id)
            .order_by(BankMovement.date.desc(), BankMovement.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return [
        MovimientoBancoOut(
            id=str(r.id),
            fecha=r.date.isoformat(),
            concepto=r.concept,
            tipo="ingreso" if r.type == "income" else "egreso",
            monto=float(r.amount),
            referencia=r.bank_reference,
            cuenta=str(r.account_id) if r.account_id else None,
            conciliado=r.reconciled,
            created_at=r.created_at.isoformat() if r.created_at else None,
            banco="",
            numero_cuenta="",
        )
        for r in rows
    ]


# ============================================================================
# BALANCES SUMMARY  (GET /finance/bank/balances)
# ============================================================================


class SaldosResumenOut(BaseModel):
    caja_total: float
    bancos_total: float
    total_disponible: float
    pendiente_conciliar: float
    ultimo_update: str


@router.get("/bank/balances", response_model=SaldosResumenOut)
def get_balances(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> SaldosResumenOut:
    """
    Resumen de saldos: caja efectivo + cuentas bancarias.

    - caja_total: suma neta de movimientos de caja (INCOME - EXPENSE)
    - bancos_total: último new_balance de cada cuenta bancaria
    - pendiente_conciliar: suma de movimientos bancarios no conciliados
    """
    tenant_id = claims["tenant_id"]

    # --- caja_total: suma neta de movimientos de caja ---
    caja_row = db.execute(
        select(func.coalesce(func.sum(CashMovement.amount), 0)).where(
            CashMovement.tenant_id == tenant_id
        )
    ).scalar()
    caja_total = float(caja_row or 0)

    # --- bancos_total: suma del último new_balance por cuenta ---
    latest_sub = (
        select(
            BankMovement.account_id,
            func.max(BankMovement.created_at).label("max_created_at"),
        )
        .where(BankMovement.tenant_id == tenant_id)
        .group_by(BankMovement.account_id)
        .subquery()
    )
    bancos_row = db.execute(
        select(func.coalesce(func.sum(BankMovement.new_balance), 0)).join(
            latest_sub,
            (BankMovement.account_id == latest_sub.c.account_id)
            & (BankMovement.created_at == latest_sub.c.max_created_at),
        )
    ).scalar()
    bancos_total = float(bancos_row or 0)

    # --- pendiente_conciliar: monto total no conciliado ---
    pendiente_row = db.execute(
        select(func.coalesce(func.sum(BankMovement.amount), 0)).where(
            BankMovement.tenant_id == tenant_id,
            BankMovement.reconciled.is_(False),
        )
    ).scalar()
    pendiente_conciliar = abs(float(pendiente_row or 0))

    return SaldosResumenOut(
        caja_total=max(caja_total, 0),
        bancos_total=max(bancos_total, 0),
        total_disponible=max(caja_total, 0) + max(bancos_total, 0),
        pendiente_conciliar=pendiente_conciliar,
        ultimo_update=datetime.now(UTC).isoformat(),
    )
