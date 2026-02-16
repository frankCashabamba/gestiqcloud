"""
POS: Tenant Endpoints
Shifts, receipts, checkout, payments
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope, require_permission
from app.db.rls import ensure_rls
from app.modules.pos.application.schemas import (
    CheckoutRequest,
    CloseShiftRequest,
    CreateReceiptRequest,
    NumberingCounterResponse,
    OpenShiftRequest,
    ReceiptResponse,
    ShiftResponse,
    ShiftSummaryResponse,
)
from app.modules.pos.application.use_cases import (
    CheckoutReceiptUseCase,
    CloseShiftUseCase,
    CreateReceiptUseCase,
    OpenShiftUseCase,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# UTILITIES
# ============================================================================


def _get_user_id(request: Request) -> UUID:
    """Get user ID from request claims."""
    claims = getattr(request.state, "access_claims", {})
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    return UUID(str(user_id))


def _get_tenant_id(request: Request) -> UUID:
    """Get tenant ID from request claims."""
    claims = getattr(request.state, "access_claims", {})
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID not found")
    return UUID(str(tenant_id))


# ============================================================================
# ENDPOINTS: SHIFTS
# ============================================================================


@router.post("/shifts/open", response_model=ShiftResponse)
def open_shift(
    payload: OpenShiftRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Open cash drawer for new shift."""
    try:
        use_case = OpenShiftUseCase()
        shift_data = use_case.execute(
            register_id=payload.register_id,
            opening_float=payload.opening_float,
            cashier_id=_get_user_id(request),
        )

        # TODO: Persist to DB
        # shift = POSShift(**shift_data)
        # db.add(shift)
        # db.commit()
        # db.refresh(shift)

        logger.info(f"Shift opened for register {payload.register_id}")
        return shift_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error opening shift")
        raise HTTPException(status_code=500, detail="Error al abrir turno")


@router.post("/shifts/{shift_id}/close", response_model=ShiftSummaryResponse)
def close_shift(
    shift_id: UUID,
    payload: CloseShiftRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Close shift and calculate variance."""
    try:
        use_case = CloseShiftUseCase()
        summary = use_case.execute(
            shift_id=shift_id,
            cash_count=payload.cash_count,
            closing_notes=payload.notes,
        )

        # TODO: Fetch receipts, calculate totals
        # receipts = db.query(POSReceipt).filter(
        #     POSReceipt.shift_id == shift_id,
        #     POSReceipt.status == "paid"
        # ).all()
        # sales_total = sum(r.total for r in receipts)

        # TODO: Update shift in DB
        # db.commit()

        logger.info(f"Shift {shift_id} closed")
        return summary

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error closing shift")
        raise HTTPException(status_code=500, detail="Error al cerrar turno")


@router.get("/shifts/{shift_id}/summary", response_model=ShiftSummaryResponse)
def get_shift_summary(
    shift_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get shift summary with totals and variance."""
    try:
        # TODO: Fetch shift, receipts, calculate
        # shift = db.query(POSShift).filter(POSShift.id == shift_id).first()
        # if not shift:
        #     raise HTTPException(status_code=404, detail="Shift not found")
        #
        # receipts = db.query(POSReceipt).filter(
        #     POSReceipt.shift_id == shift_id
        # ).all()

        return {
            "shift_id": shift_id,
            "register_id": UUID(int=0),
            "opened_at": datetime.utcnow(),
            "closed_at": datetime.utcnow(),
            "opening_float": Decimal("0"),
            "cash_count": Decimal("0"),
            "receipts_count": 0,
            "sales_total": Decimal("0"),
            "expected_cash": Decimal("0"),
            "variance": Decimal("0"),
            "variance_pct": Decimal("0"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching shift summary")
        raise HTTPException(status_code=500, detail="Error")


# ============================================================================
# ENDPOINTS: RECEIPTS
# ============================================================================


@router.post("/receipts", response_model=dict)
def create_receipt(
    payload: CreateReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create receipt in draft state."""
    try:
        use_case = CreateReceiptUseCase()
        receipt_data = use_case.execute(
            register_id=payload.register_id,
            shift_id=payload.shift_id,
            lines=payload.lines,
            notes=payload.notes,
        )

        # TODO: Persist receipt + lines to DB
        # receipt = POSReceipt(**receipt_data)
        # db.add(receipt)
        # for line in payload.lines:
        #     db.add(POSReceiptLine(receipt_id=receipt.id, **line.dict()))
        # db.commit()

        logger.info(f"Receipt created for shift {payload.shift_id}")
        return {
            "receipt_id": uuid4(),
            "number": "TKT-001",
            "status": "draft",
            "subtotal": receipt_data.get("subtotal"),
            "tax": receipt_data.get("tax"),
            "total": receipt_data.get("total"),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating receipt")
        raise HTTPException(status_code=500, detail="Error al crear recibo")


@router.post("/receipts/{receipt_id}/checkout", response_model=dict)
def checkout(
    receipt_id: UUID,
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Pay receipt (checkout).

    Operations:
    1. Validate payments
    2. Deduct stock from inventory
    3. Create journal entry in accounting
    4. Update receipt status to paid
    """
    try:
        use_case = CheckoutReceiptUseCase()
        result = use_case.execute(
            receipt_id=receipt_id,
            payments=payload.payments,
            warehouse_id=payload.warehouse_id,
        )

        # TODO: Execute integrations
        # 1. Update receipt
        # receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
        # receipt.status = "paid"
        # receipt.paid_at = datetime.utcnow()

        # 2. Deduct stock
        # inv_svc = InventoryCostingService(db)
        # for line in receipt.lines:
        #     inv_svc.deduct_stock(...)

        # 3. Create journal entry
        # acct_svc = AccountingService(db)
        # acct_svc.create_entry_from_receipt(receipt_id)

        # db.commit()

        logger.info(f"Receipt {receipt_id} paid")
        return {
            "receipt_id": receipt_id,
            "status": "paid",
            "paid_at": datetime.utcnow(),
            "payments": payload.payments,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error during checkout")
        raise HTTPException(status_code=500, detail="Error al procesar pago")


@router.get("/receipts/{receipt_id}", response_model=dict)
def get_receipt(
    receipt_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get receipt details."""
    try:
        # TODO: Fetch from DB
        # receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
        # if not receipt:
        #     raise HTTPException(status_code=404, detail="Receipt not found")
        # return receipt

        return {
            "id": receipt_id,
            "number": "TKT-001",
            "status": "draft",
            "total": Decimal("0"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching receipt")
        raise HTTPException(status_code=500, detail="Error")


# ============================================================================
# ENDPOINTS: NUMBERING
# ============================================================================


@router.get("/numbering/{doc_type}/{series}/{year}", response_model=NumberingCounterResponse)
def get_numbering_counter(
    doc_type: str,
    series: str,
    year: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get current numbering counter."""
    try:
        # TODO: Fetch from numbering_counters table
        # counter = db.query(NumberingCounter).filter(
        #     NumberingCounter.doc_type == doc_type,
        #     NumberingCounter.series == series,
        #     NumberingCounter.year == year
        # ).first()

        return {
            "doc_type": doc_type,
            "series": series,
            "year": year,
            "current_no": 0,
            "updated_at": datetime.utcnow(),
        }

    except Exception as e:
        logger.exception("Error fetching numbering counter")
        raise HTTPException(status_code=500, detail="Error")
