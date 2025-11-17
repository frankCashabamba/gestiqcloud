"""
ElectricSQL Shapes Configuration for Offline-First Sync

Defines the data shapes that should be synchronized for offline usage.
Based on tenant_id for multi-tenant isolation.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db

from .electric_conflicts import handle_sync_conflicts

router = APIRouter(prefix="/api/v1/electric", tags=["electric"])


def get_tenant_shapes(tenant_id: str) -> dict[str, Any]:
    """
    Define shapes for a specific tenant.

    Shapes tell ElectricSQL what data to sync for offline usage.
    """
    return {
        "products": {"table": "products", "where": f"tenant_id = '{tenant_id}'"},
        "clients": {"table": "clients", "where": f"tenant_id = '{tenant_id}'"},
        "pos_receipts": {
            "table": "pos_receipts",
            "where": f"tenant_id = '{tenant_id}'",
        },
        "pos_receipt_lines": {
            "table": "pos_receipt_lines",
            "where": f"receipt_id IN (SELECT id FROM pos_receipts WHERE tenant_id = '{tenant_id}')",
        },
        "pos_payments": {
            "table": "pos_payments",
            "where": f"receipt_id IN (SELECT id FROM pos_receipts WHERE tenant_id = '{tenant_id}')",
        },
        "stock_items": {"table": "stock_items", "where": f"tenant_id = '{tenant_id}'"},
        "stock_moves": {"table": "stock_moves", "where": f"tenant_id = '{tenant_id}'"},
    }


@router.get("/shapes")
async def get_shapes(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get ElectricSQL shapes for the current tenant.

    This endpoint is called by ElectricSQL to determine what data to sync.
    """
    tenant_id = request.state.access_claims.get("tenant_id")

    if not tenant_id:
        return {"shapes": {}}

    shapes = get_tenant_shapes(tenant_id)

    return {"shapes": shapes, "meta": {"tenant_id": tenant_id, "version": "1.0"}}


@router.post("/sync-status")
async def update_sync_status(
    request: Request, status: dict[str, Any], db: Session = Depends(get_db)
):
    """
    Handle sync status updates from ElectricSQL.

    Called when sync operations complete or fail.
    Processes conflicts if any occurred during sync.
    """
    tenant_id = request.state.access_claims.get("tenant_id")

    # Handle conflicts if present
    conflicts = status.get("conflicts", [])
    if conflicts:
        resolved_changes = await handle_sync_conflicts(conflicts, tenant_id, db)
        print(f"Resolved {len(resolved_changes)} conflicts for tenant {tenant_id}")

        return {"status": "acknowledged", "resolved_conflicts": resolved_changes}

    # Log sync status for monitoring
    print(f"Sync status for tenant {tenant_id}: {status}")

    return {"status": "acknowledged"}
