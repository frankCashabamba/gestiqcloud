"""
SALES: Tenant Endpoints
Sales orders, approvals, invoicing
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
from app.modules.sales.application.use_cases import (
    ApproveSalesOrderUseCase,
    CancelSalesOrderUseCase,
    CreateInvoiceFromOrderUseCase,
    CreateSalesOrderUseCase,
    GetSalesOrderUseCase,
)

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class SalesOrderLineRequest(BaseModel):
    """Sales order line."""

    product_id: UUID
    qty: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=4)
    discount_pct: Decimal = Field(ge=0, le=100, decimal_places=2, default=Decimal("0"))


class CreateSalesOrderRequest(BaseModel):
    """Create sales order request."""

    customer_id: UUID
    lines: list[SalesOrderLineRequest] = Field(min_length=1)
    notes: str | None = Field(None, max_length=500)


class CancelOrderRequest(BaseModel):
    """Cancel order request."""

    reason: str = Field(max_length=500)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/sales",
    tags=["Sales"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("sales.view")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# UTILITIES
# ============================================================================


def _get_user_id(request: Request) -> UUID:
    """Get user ID from claims."""
    claims = getattr(request.state, "access_claims", {})
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    return UUID(str(user_id))


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/orders", response_model=dict)
def create_sales_order(
    payload: CreateSalesOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create sales order in draft state."""
    try:
        use_case = CreateSalesOrderUseCase()
        order_data = use_case.execute(
            customer_id=payload.customer_id,
            lines=[l.dict() for l in payload.lines],
            notes=payload.notes,
        )

        # TODO: Persist to DB
        # order = SalesOrder(**order_data)
        # db.add(order)
        # for line in payload.lines:
        #     db.add(SalesOrderLine(order_id=order.id, **line.dict()))
        # db.commit()

        logger.info(f"Sales order created for customer {payload.customer_id}")
        return {
            "order_id": order_data.get("order_id"),
            "order_number": order_data.get("order_number"),
            "status": "draft",
            "customer_id": payload.customer_id,
            "total": order_data.get("total"),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating sales order")
        raise HTTPException(status_code=500, detail="Error al crear orden")


@router.patch("/orders/{order_id}/approve", response_model=dict)
def approve_sales_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Approve sales order (draft → approved)."""
    try:
        use_case = ApproveSalesOrderUseCase()
        result = use_case.execute(
            order_id=order_id,
            approved_by=_get_user_id(request),
        )

        # TODO: Update order status in DB
        # db.query(SalesOrder).filter(SalesOrder.id == order_id).update({
        #     "status": "approved",
        #     "approved_at": datetime.utcnow(),
        #     "approved_by": user_id
        # })
        # db.commit()

        logger.info(f"Sales order {order_id} approved")
        return {
            "order_id": order_id,
            "status": "approved",
            "approved_at": datetime.utcnow(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error approving order")
        raise HTTPException(status_code=500, detail="Error")


@router.post("/orders/{order_id}/invoice", response_model=dict)
def create_invoice_from_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create invoice from approved sales order."""
    try:
        # TODO: Fetch order from DB
        use_case = CreateInvoiceFromOrderUseCase()
        invoice_data = use_case.execute(
            order_id=order_id,
            order_number="ORD-001",  # TODO: From order
            customer_id=UUID(int=0),  # TODO: From order
            lines=[],  # TODO: From order
            subtotal=Decimal("0"),  # TODO: From order
            tax=Decimal("0"),  # TODO: From order
        )

        # TODO: Update order status + create invoice
        # db.query(SalesOrder).filter(SalesOrder.id == order_id).update({
        #     "status": "invoiced",
        #     "invoice_id": invoice_data["invoice_id"]
        # })
        # db.commit()

        logger.info(f"Invoice created from order {order_id}")
        return invoice_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating invoice")
        raise HTTPException(status_code=500, detail="Error")


@router.patch("/orders/{order_id}/cancel", response_model=dict)
def cancel_order(
    order_id: UUID,
    payload: CancelOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cancel sales order."""
    try:
        use_case = CancelSalesOrderUseCase()
        result = use_case.execute(
            order_id=order_id,
            reason=payload.reason,
            cancelled_by=_get_user_id(request),
        )

        # TODO: Update status in DB
        # db.commit()

        logger.info(f"Sales order {order_id} cancelled")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error cancelling order")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/orders", response_model=dict)
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List sales orders."""
    try:
        # TODO: Fetch from DB with pagination
        # orders = db.query(SalesOrder).offset(skip).limit(limit).all()

        return {
            "orders": [],
            "total_count": 0,
            "page": 1,
            "page_size": limit,
        }

    except Exception as e:
        logger.exception("Error listing orders")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/orders/{order_id}", response_model=dict)
def get_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get sales order details."""
    try:
        use_case = GetSalesOrderUseCase()
        order = use_case.execute(order_id=order_id)

        # TODO: Fetch from DB
        # order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()

        return order

    except Exception as e:
        logger.exception("Error fetching order")
        raise HTTPException(status_code=500, detail="Error")
