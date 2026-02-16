"""
INVENTORY: Tenant Endpoints
Stock management, receives, adjustments
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope, require_permission
from app.db.rls import ensure_rls
from app.modules.inventory.application.use_cases import (
    AdjustStockUseCase,
    CalculateInventoryValueUseCase,
    CreateWarehouseUseCase,
    GetLowStockAlertsUseCase,
    ReceiveStockUseCase,
    TransferStockUseCase,
)

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class ReceiveStockRequest(BaseModel):
    """Receive stock from purchase."""

    warehouse_id: UUID
    lines: list[dict]
    po_id: UUID | None = None


class AdjustStockRequest(BaseModel):
    """Adjust stock manually."""

    warehouse_id: UUID
    product_id: UUID
    qty_adjustment: Decimal
    reason: str = Field(max_length=500)


class TransferStockRequest(BaseModel):
    """Transfer stock between warehouses."""

    from_warehouse_id: UUID
    to_warehouse_id: UUID
    product_id: UUID
    qty: Decimal = Field(gt=0)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("inventory.view")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/stock/receive", response_model=dict)
def receive_stock(
    payload: ReceiveStockRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive stock from purchase order."""
    try:
        use_case = ReceiveStockUseCase()
        receipt = use_case.execute(
            warehouse_id=payload.warehouse_id,
            purchase_order_id=payload.po_id,
            lines=payload.lines,
        )

        # TODO: Persist receipt + stock moves
        # db.add(StockReceipt(**receipt))
        # db.commit()

        logger.info(f"Stock received for warehouse {payload.warehouse_id}")
        return receipt

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error receiving stock")
        raise HTTPException(status_code=500, detail="Error al recibir stock")


@router.post("/stock/adjust", response_model=dict)
def adjust_stock(
    payload: AdjustStockRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Adjust stock manually (damage, loss, etc)."""
    try:
        use_case = AdjustStockUseCase()
        move = use_case.execute(
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            qty_adjustment=payload.qty_adjustment,
            reason=payload.reason,
        )

        # TODO: Create stock move in DB
        # db.add(StockMove(**move))
        # db.commit()

        logger.info(f"Stock adjusted for product {payload.product_id}: {payload.qty_adjustment}")
        return move

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error adjusting stock")
        raise HTTPException(status_code=500, detail="Error")


@router.post("/stock/transfer", response_model=dict)
def transfer_stock(
    payload: TransferStockRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Transfer stock between warehouses."""
    try:
        use_case = TransferStockUseCase()
        transfer = use_case.execute(
            from_warehouse_id=payload.from_warehouse_id,
            to_warehouse_id=payload.to_warehouse_id,
            product_id=payload.product_id,
            qty=payload.qty,
        )

        # TODO: Update both warehouses, create moves
        # db.commit()

        logger.info(f"Stock transferred: {payload.qty} units")
        return transfer

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error transferring stock")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/summary", response_model=dict)
def get_inventory_summary(
    request: Request,
    db: Session = Depends(get_db),
    warehouse_id: UUID | None = None,
):
    """Get inventory value summary."""
    try:
        use_case = CalculateInventoryValueUseCase()
        summary = use_case.execute(
            warehouse_id=warehouse_id,
        )

        return summary

    except Exception as e:
        logger.exception("Error calculating inventory value")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/alerts", response_model=dict)
def get_low_stock_alerts(
    request: Request,
    db: Session = Depends(get_db),
    warehouse_id: UUID | None = None,
):
    """Get low stock alerts."""
    try:
        use_case = GetLowStockAlertsUseCase()
        alerts = use_case.execute(
            warehouse_id=warehouse_id,
            threshold_pct=20,
        )

        return alerts

    except Exception as e:
        logger.exception("Error fetching alerts")
        raise HTTPException(status_code=500, detail="Error")
