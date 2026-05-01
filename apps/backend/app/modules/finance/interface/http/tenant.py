"""Finance Module - HTTP API (Tenant)"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.core.permissions import PERM_FINANCE_CASHBOX_WRITE
from app.db.rls import ensure_rls
from app.models.finance.banco import BankMovement
from app.models.finance.cash_management import CashMovement
from app.modules.finance.application.cash_service import CashPositionService
from app.schemas.finance_caja import CashMovementCreate, CashMovementResponse

logger = logging.getLogger(__name__)

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


class CashMovementOut(BaseModel):
    id: str
    date: str
    description: str
    type: str  # "income" | "expense"
    amount: float
    reference: str | None = None
    account: str | None = None
    reconciled: bool = True
    created_at: str | None = None


@router.get("/cashbox/movements", response_model=list[CashMovementOut])
def list_cashbox_movements(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[CashMovementOut]:
    """List tenant cash movements."""
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
        CashMovementOut(
            id=str(r.id),
            date=r.date.isoformat(),
            description=r.description,
            type="income" if r.type == "INCOME" else "expense",
            amount=float(r.amount),
            reference=str(r.ref_doc_id) if r.ref_doc_id else None,
            account=str(r.cash_box_id) if r.cash_box_id else None,
            reconciled=True,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@router.post(
    "/cashbox/movements",
    response_model=CashMovementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERM_FINANCE_CASHBOX_WRITE))],
)
def create_cashbox_movement(
    body: CashMovementCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> CashMovementResponse:
    """Registra un movimiento manual de caja y genera el asiento contable."""
    tenant_id: UUID = claims["tenant_id"]
    user_id: UUID | None = claims.get("user_id")

    movement = CashMovement(
        tenant_id=tenant_id,
        user_id=user_id,
        type=body.movement_type,
        category=body.category,
        amount=body.amount,
        currency=body.currency or "USD",
        description=body.description,
        notes=body.notes,
        date=body.date,
        ref_doc_type=body.ref_doc_type,
        ref_doc_id=body.ref_doc_id,
        cash_box_id=body.cash_box_id,
    )
    db.add(movement)
    db.flush()
    db.commit()
    db.refresh(movement)

    # Asiento contable automático — no bloquea si falla.
    try:
        from app.modules.finance.application.journal import post_cash_movement_entry

        post_cash_movement_entry(db, movement, user_id)
        db.commit()
    except Exception:  # noqa: BLE001
        logger.warning(
            "post_cash_movement_entry hook failed for movement_id=%s",
            movement.id,
            exc_info=True,
        )
        db.rollback()

    return CashMovementResponse.model_validate(movement)


# ============================================================================
# BANK MOVEMENTS  (GET /finance/bank/movements)
# ============================================================================


class BankMovementOut(CashMovementOut):
    bank: str = ""
    account_number: str = ""


@router.get("/bank/movements", response_model=list[BankMovementOut])
def list_bank_movements(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[BankMovementOut]:
    """List tenant bank movements."""
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
        BankMovementOut(
            id=str(r.id),
            date=r.date.isoformat(),
            description=r.concept,
            type="income" if r.type == "income" else "expense",
            amount=float(r.amount),
            reference=r.bank_reference,
            account=str(r.account_id) if r.account_id else None,
            reconciled=r.reconciled,
            created_at=r.created_at.isoformat() if r.created_at else None,
            bank="",
            account_number="",
        )
        for r in rows
    ]


# ============================================================================
# BALANCES SUMMARY  (GET /finance/bank/balances)
# ============================================================================


class CashBalancesSummaryOut(BaseModel):
    cash_total: float
    bank_total: float
    available_total: float
    pending_reconciliation: float
    last_update: str


@router.get("/bank/balances", response_model=CashBalancesSummaryOut)
def get_balances(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> CashBalancesSummaryOut:
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
        select(func.coalesce(func.sum(BankMovement.new_balance), 0))
        .join(
            latest_sub,
            (BankMovement.account_id == latest_sub.c.account_id)
            & (BankMovement.created_at == latest_sub.c.max_created_at),
        )
        .where(BankMovement.tenant_id == tenant_id)
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

    return CashBalancesSummaryOut(
        cash_total=max(caja_total, 0),
        bank_total=max(bancos_total, 0),
        available_total=max(caja_total, 0) + max(bancos_total, 0),
        pending_reconciliation=pendiente_conciliar,
        last_update=datetime.now(UTC).isoformat(),
    )
