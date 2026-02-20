"""Service for managing stock transfers between warehouses"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.inventory.transfers import StockTransfer, TransferStatus
from app.services.inventory_costing import InventoryCostingService


class StockTransferService:
    """Service for creating and managing warehouse stock transfers"""

    def __init__(self, db: Session):
        self.db = db
        self.costing_service = InventoryCostingService(db)

    def create_transfer(
        self,
        tenant_id: UUID,
        from_warehouse_id: UUID,
        to_warehouse_id: UUID,
        product_id: UUID,
        quantity: float,
        reason: str | None = None,
        notes: str | None = None,
    ) -> StockTransfer:
        """Create a new stock transfer (initially in DRAFT status)"""
        if from_warehouse_id == to_warehouse_id:
            raise ValueError("Source and destination warehouses must be different")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        transfer = StockTransfer(
            tenant_id=str(tenant_id),
            from_warehouse_id=str(from_warehouse_id),
            to_warehouse_id=str(to_warehouse_id),
            product_id=str(product_id),
            quantity=quantity,
            status=TransferStatus.DRAFT,
            reason=reason,
            notes=notes,
        )
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def start_transfer(self, transfer_id: UUID, tenant_id: UUID) -> StockTransfer:
        """Mark transfer as IN_TRANSIT and deduct stock from source warehouse"""
        transfer = self._get_transfer(transfer_id, tenant_id)

        if transfer.status != TransferStatus.DRAFT:
            raise ValueError(f"Cannot start transfer with status '{transfer.status}'")

        # Check stock availability
        self._validate_stock_available(
            tenant_id,
            transfer.from_warehouse_id,
            transfer.product_id,
            Decimal(str(transfer.quantity)),
        )

        # Deduct from source warehouse
        self.costing_service.apply_outbound(
            str(tenant_id),
            str(transfer.from_warehouse_id),
            str(transfer.product_id),
            qty=Decimal(str(transfer.quantity)),
            allow_negative=False,
        )

        transfer.status = TransferStatus.IN_TRANSIT
        transfer.started_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def complete_transfer(self, transfer_id: UUID, tenant_id: UUID) -> StockTransfer:
        """Mark transfer as COMPLETED and add stock to destination warehouse"""
        transfer = self._get_transfer(transfer_id, tenant_id)

        if transfer.status != TransferStatus.IN_TRANSIT:
            raise ValueError(
                f"Can only complete transfers in IN_TRANSIT status, current: '{transfer.status}'"
            )

        # Add to destination warehouse using average cost from source
        # For now, we use a standard cost transfer (not LIFO/FIFO)
        # In production, you might want to preserve the layer information
        avg_unit_cost = Decimal("0")  # Will be calculated or provided

        self.costing_service.apply_inbound(
            str(tenant_id),
            str(transfer.to_warehouse_id),
            str(transfer.product_id),
            qty=Decimal(str(transfer.quantity)),
            unit_cost=avg_unit_cost,
        )

        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def cancel_transfer(self, transfer_id: UUID, tenant_id: UUID) -> StockTransfer:
        """Cancel a transfer and restore stock if already deducted"""
        transfer = self._get_transfer(transfer_id, tenant_id)

        if transfer.status == TransferStatus.COMPLETED:
            raise ValueError("Cannot cancel completed transfers")

        # If IN_TRANSIT, restore stock to source
        if transfer.status == TransferStatus.IN_TRANSIT:
            self.costing_service.apply_inbound(
                str(tenant_id),
                str(transfer.from_warehouse_id),
                str(transfer.product_id),
                qty=Decimal(str(transfer.quantity)),
                unit_cost=Decimal("0"),  # Restoration, cost doesn't matter
            )

        transfer.status = TransferStatus.CANCELLED
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def get_transfer(self, transfer_id: UUID, tenant_id: UUID) -> StockTransfer:
        """Get a transfer by ID"""
        return self._get_transfer(transfer_id, tenant_id)

    def list_transfers(
        self,
        tenant_id: UUID,
        status: str | None = None,
        product_id: UUID | None = None,
        from_warehouse_id: UUID | None = None,
        to_warehouse_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[StockTransfer], int]:
        """List transfers with optional filters"""
        query = self.db.query(StockTransfer).filter(StockTransfer.tenant_id == str(tenant_id))

        if status:
            query = query.filter(StockTransfer.status == status)
        if product_id:
            query = query.filter(StockTransfer.product_id == str(product_id))
        if from_warehouse_id:
            query = query.filter(StockTransfer.from_warehouse_id == str(from_warehouse_id))
        if to_warehouse_id:
            query = query.filter(StockTransfer.to_warehouse_id == str(to_warehouse_id))

        total = query.count()
        transfers = (
            query.order_by(StockTransfer.created_at.desc()).offset(offset).limit(limit).all()
        )

        return transfers, total

    def _get_transfer(self, transfer_id: UUID, tenant_id: UUID) -> StockTransfer:
        """Get transfer and verify tenant access"""
        transfer = (
            self.db.query(StockTransfer)
            .filter(
                StockTransfer.id == str(transfer_id),
                StockTransfer.tenant_id == str(tenant_id),
            )
            .first()
        )

        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")

        return transfer

    def _validate_stock_available(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        product_id: UUID,
        quantity: Decimal,
    ) -> None:
        """Validate that sufficient stock exists in warehouse"""
        # This is simplified - in production you'd query the actual inventory
        # For now, trust the costing service to enforce this
        pass
