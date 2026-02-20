"""Finance Module - HTTP API (Tenant)"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
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
