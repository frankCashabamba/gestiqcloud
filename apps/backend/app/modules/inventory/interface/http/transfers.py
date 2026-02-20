"""HTTP endpoints for stock transfers"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.inventory.transfers import StockTransfer, TransferStatus
from app.modules.inventory.application.stock_transfer_service import StockTransferService

router = APIRouter(
    prefix="/stock_transfers",
    tags=["Inventory - Transfers"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_uuid(request: Request) -> UUID:
    """Extract tenant_id from request"""
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid tenant_id")


class StockTransferCreateRequest(BaseModel):
    """Request to create a stock transfer"""

    from_warehouse_id: str
    to_warehouse_id: str
    product_id: str
    quantity: float = Field(gt=0)
    reason: str | None = None
    notes: str | None = None


class StockTransferResponse(BaseModel):
    """Response model for stock transfer"""

    id: str
    tenant_id: str
    from_warehouse_id: str
    to_warehouse_id: str
    product_id: str
    quantity: float
    status: str
    reason: str | None
    notes: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


@router.post("", response_model=StockTransferResponse, status_code=201)
def create_transfer(
    request: Request,
    payload: StockTransferCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new stock transfer (DRAFT status).

    - **from_warehouse_id**: Source warehouse UUID
    - **to_warehouse_id**: Destination warehouse UUID
    - **product_id**: Product to transfer UUID
    - **quantity**: Amount to transfer (positive number)
    - **reason**: Optional reason code (e.g., "rebalance", "repair", "transfer")
    - **notes**: Optional notes

    Returns the created transfer in DRAFT status.
    """
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfer = service.create_transfer(
            tenant_id=tenant_id,
            from_warehouse_id=UUID(payload.from_warehouse_id),
            to_warehouse_id=UUID(payload.to_warehouse_id),
            product_id=UUID(payload.product_id),
            quantity=payload.quantity,
            reason=payload.reason,
            notes=payload.notes,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating transfer: {str(e)}")


@router.get("", response_model=dict)
def list_transfers(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = Query(None, regex="^(draft|in_transit|completed|cancelled)$"),
    product_id: str | None = None,
    from_warehouse_id: str | None = None,
    to_warehouse_id: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List stock transfers for the tenant.

    - **status**: Filter by status (draft, in_transit, completed, cancelled)
    - **product_id**: Filter by product UUID
    - **from_warehouse_id**: Filter by source warehouse UUID
    - **to_warehouse_id**: Filter by destination warehouse UUID
    - **limit**: Max results per page (max 500)
    - **offset**: Pagination offset
    """
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfers, total = service.list_transfers(
            tenant_id=tenant_id,
            status=status,
            product_id=UUID(product_id) if product_id else None,
            from_warehouse_id=UUID(from_warehouse_id) if from_warehouse_id else None,
            to_warehouse_id=UUID(to_warehouse_id) if to_warehouse_id else None,
            limit=limit,
            offset=offset,
        )

        return {
            "data": [StockTransferResponse.model_validate(t) for t in transfers],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing transfers: {str(e)}")


@router.get("/{transfer_id}", response_model=StockTransferResponse)
def get_transfer(
    request: Request,
    transfer_id: str = Path(..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
):
    """Get a specific stock transfer by ID"""
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfer = service.get_transfer(UUID(transfer_id), tenant_id)
        return StockTransferResponse.model_validate(transfer)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving transfer: {str(e)}")


@router.post("/{transfer_id}/start", response_model=StockTransferResponse)
def start_transfer(
    request: Request,
    transfer_id: str = Path(..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
):
    """
    Start a transfer (move to IN_TRANSIT status).

    - Deducts stock from source warehouse
    - Requires transfer to be in DRAFT status
    - Validates stock availability
    """
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfer = service.start_transfer(UUID(transfer_id), tenant_id)
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error starting transfer: {str(e)}")


@router.post("/{transfer_id}/complete", response_model=StockTransferResponse)
def complete_transfer(
    request: Request,
    transfer_id: str = Path(..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
):
    """
    Complete a transfer (move to COMPLETED status).

    - Adds stock to destination warehouse
    - Requires transfer to be in IN_TRANSIT status
    - Updates completed_at timestamp
    """
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfer = service.complete_transfer(UUID(transfer_id), tenant_id)
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error completing transfer: {str(e)}")


@router.post("/{transfer_id}/cancel", response_model=StockTransferResponse)
def cancel_transfer(
    request: Request,
    transfer_id: str = Path(..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
):
    """
    Cancel a transfer.

    - Restores stock to source warehouse if IN_TRANSIT
    - Cannot cancel COMPLETED transfers
    - Sets status to CANCELLED
    """
    tenant_id = _tenant_uuid(request)

    try:
        service = StockTransferService(db)
        transfer = service.cancel_transfer(UUID(transfer_id), tenant_id)
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling transfer: {str(e)}")
