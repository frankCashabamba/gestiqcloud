"""Tests for stock transfer functionality"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.inventory.transfers import TransferStatus
from app.modules.inventory.application.stock_transfer_service import StockTransferService


@pytest.fixture
def transfer_setup(db: Session, tenant_minimal):
    """Setup warehouses and products for transfer tests"""
    tid = tenant_minimal["tenant_id"]
    tid_str = tenant_minimal["tenant_id_str"]

    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific test")

    db.execute(text(f"SET app.tenant_id = '{tid_str}'"))
    db.execute(text("SET session_replication_role = REPLICA"))

    # Create warehouses
    wh1_id = db.execute(text("SELECT gen_random_uuid()")).scalar()
    wh2_id = db.execute(text("SELECT gen_random_uuid()")).scalar()

    db.execute(
        text(
            "INSERT INTO warehouses (id, tenant_id, code, name, active) "
            "VALUES (:id, :tid, :code, :name, TRUE)"
        ),
        {"id": wh1_id, "tid": tid, "code": "WH1", "name": "Warehouse 1"},
    )
    db.execute(
        text(
            "INSERT INTO warehouses (id, tenant_id, code, name, active) "
            "VALUES (:id, :tid, :code, :name, TRUE)"
        ),
        {"id": wh2_id, "tid": tid, "code": "WH2", "name": "Warehouse 2"},
    )

    # Create product
    prod_id = db.execute(text("SELECT gen_random_uuid()")).scalar()
    db.execute(
        text(
            "INSERT INTO products (id, tenant_id, name, active, stock, unit) "
            "VALUES (:id, :tid, :name, TRUE, 0, 'unit')"
        ),
        {"id": prod_id, "tid": tid, "name": "Transfer Test Product"},
    )

    db.commit()

    return {
        "tenant_id": tid,
        "warehouse_1_id": wh1_id,
        "warehouse_2_id": wh2_id,
        "product_id": prod_id,
    }


def test_create_transfer_draft(db: Session, transfer_setup):
    """Test creating a transfer in DRAFT status"""
    setup = transfer_setup
    service = StockTransferService(db)

    transfer = service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=100.0,
        reason="rebalance",
        notes="Test transfer",
    )

    assert transfer.status == TransferStatus.DRAFT
    assert float(transfer.quantity) == 100.0
    assert transfer.reason == "rebalance"
    assert transfer.started_at is None
    assert transfer.completed_at is None
    db.commit()


def test_create_transfer_same_warehouse_fails(db: Session, transfer_setup):
    """Test that transfer between same warehouse fails"""
    setup = transfer_setup
    service = StockTransferService(db)

    with pytest.raises(ValueError, match="different"):
        service.create_transfer(
            tenant_id=setup["tenant_id"],
            from_warehouse_id=setup["warehouse_1_id"],
            to_warehouse_id=setup["warehouse_1_id"],  # Same warehouse
            product_id=setup["product_id"],
            quantity=100.0,
        )


def test_create_transfer_negative_quantity_fails(db: Session, transfer_setup):
    """Test that negative quantity fails"""
    setup = transfer_setup
    service = StockTransferService(db)

    with pytest.raises(ValueError, match="positive"):
        service.create_transfer(
            tenant_id=setup["tenant_id"],
            from_warehouse_id=setup["warehouse_1_id"],
            to_warehouse_id=setup["warehouse_2_id"],
            product_id=setup["product_id"],
            quantity=-10.0,  # Negative
        )


def test_start_transfer_deducts_stock(db: Session, transfer_setup):
    """Test that starting a transfer deducts stock from source"""
    from app.services.inventory_costing import InventoryCostingService

    setup = transfer_setup
    service = StockTransferService(db)
    costing = InventoryCostingService(db)

    # Add stock to warehouse 1
    costing.apply_inbound(
        str(setup["tenant_id"]),
        str(setup["warehouse_1_id"]),
        str(setup["product_id"]),
        qty=Decimal("100"),
        unit_cost=Decimal("10"),
        initial_qty=Decimal("0"),
        initial_avg_cost=Decimal("0"),
    )
    db.commit()

    # Create and start transfer
    transfer = service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=50.0,
    )

    started = service.start_transfer(transfer.id, setup["tenant_id"])
    assert started.status == TransferStatus.IN_TRANSIT
    assert started.started_at is not None

    # Verify stock was deducted
    state = costing._ensure_state_row(
        str(setup["tenant_id"]),
        str(setup["warehouse_1_id"]),
        str(setup["product_id"]),
    )
    assert float(state.on_hand_qty) == 50.0  # 100 - 50
    db.commit()


def test_start_transfer_insufficient_stock_fails(db: Session, transfer_setup):
    """Test that starting transfer with insufficient stock fails"""
    setup = transfer_setup
    service = StockTransferService(db)

    # Create transfer without adding stock
    transfer = service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=100.0,  # No stock available
    )

    # Attempt to start should fail
    with pytest.raises(Exception):  # HTTPException or inventory error
        service.start_transfer(transfer.id, setup["tenant_id"])
    db.commit()


def test_cancel_transfer_draft(db: Session, transfer_setup):
    """Test cancelling a DRAFT transfer"""
    setup = transfer_setup
    service = StockTransferService(db)

    transfer = service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=50.0,
    )

    cancelled = service.cancel_transfer(transfer.id, setup["tenant_id"])
    assert cancelled.status == TransferStatus.CANCELLED
    db.commit()


def test_cancel_transfer_in_transit_restores_stock(db: Session, transfer_setup):
    """Test that cancelling IN_TRANSIT transfer restores stock"""
    from app.services.inventory_costing import InventoryCostingService

    setup = transfer_setup
    service = StockTransferService(db)
    costing = InventoryCostingService(db)

    # Add stock
    costing.apply_inbound(
        str(setup["tenant_id"]),
        str(setup["warehouse_1_id"]),
        str(setup["product_id"]),
        qty=Decimal("100"),
        unit_cost=Decimal("10"),
        initial_qty=Decimal("0"),
        initial_avg_cost=Decimal("0"),
    )
    db.commit()

    # Create and start transfer
    transfer = service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=50.0,
    )
    service.start_transfer(transfer.id, setup["tenant_id"])
    db.commit()

    # Cancel transfer
    cancelled = service.cancel_transfer(transfer.id, setup["tenant_id"])
    assert cancelled.status == TransferStatus.CANCELLED

    # Verify stock was restored
    state = costing._ensure_state_row(
        str(setup["tenant_id"]),
        str(setup["warehouse_1_id"]),
        str(setup["product_id"]),
    )
    assert float(state.on_hand_qty) == 100.0  # Restored to original
    db.commit()


def test_list_transfers_filtered_by_status(db: Session, transfer_setup):
    """Test listing transfers filtered by status"""
    setup = transfer_setup
    service = StockTransferService(db)

    # Create multiple transfers
    service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=50.0,
    )
    service.create_transfer(
        tenant_id=setup["tenant_id"],
        from_warehouse_id=setup["warehouse_1_id"],
        to_warehouse_id=setup["warehouse_2_id"],
        product_id=setup["product_id"],
        quantity=25.0,
    )
    db.commit()

    # List only DRAFT transfers
    transfers, total = service.list_transfers(
        tenant_id=setup["tenant_id"],
        status=TransferStatus.DRAFT,
    )

    assert total == 2
    assert len(transfers) == 2
    assert all(t.status == TransferStatus.DRAFT for t in transfers)
    db.commit()
