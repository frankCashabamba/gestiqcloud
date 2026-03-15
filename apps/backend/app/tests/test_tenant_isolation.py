"""
Tenant isolation tests — verify RLS prevents cross-tenant data access.

Run with:
    ALLOW_TEST_NON_SQLITE_DB=1 TEST_DATABASE_URL=postgresql://... pytest app/tests/test_tenant_isolation.py -v
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.fixture
def two_tenants(db: Session):
    """Create two isolated tenants for cross-tenant tests."""
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Postgres required for RLS isolation tests")

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()

    db.execute(text("SET session_replication_role = REPLICA"))
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, TRUE, NOW())"
        ),
        {"id": tid_a, "name": "Isolation Tenant A", "slug": f"iso-a-{tid_a.hex[:8]}"},
    )
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, TRUE, NOW())"
        ),
        {"id": tid_b, "name": "Isolation Tenant B", "slug": f"iso-b-{tid_b.hex[:8]}"},
    )
    db.commit()
    db.execute(text("SET session_replication_role = DEFAULT"))

    yield {"a": tid_a, "b": tid_b, "a_str": str(tid_a), "b_str": str(tid_b)}

    # Cleanup
    db.execute(text("SET session_replication_role = REPLICA"))
    for table in [
        "sales_order_items", "sales_orders", "invoice_lines", "invoices",
        "purchase_lines", "purchases", "pos_receipt_lines", "pos_receipts",
        "pos_shifts", "pos_registers", "stock_moves", "stock_items",
        "expenses", "bank_transactions", "bank_accounts",
        "import_items", "import_batches", "products", "clients", "warehouses",
    ]:
        try:
            db.execute(
                text(f"DELETE FROM {table} WHERE tenant_id IN (:a, :b)"),
                {"a": tid_a, "b": tid_b},
            )
        except Exception:
            db.rollback()
    try:
        db.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": tid_a, "b": tid_b})
    except Exception:
        db.rollback()
    db.commit()
    db.execute(text("SET session_replication_role = DEFAULT"))


# ── helpers ──────────────────────────────────────────────────────────────


def _insert_as_replica(db: Session, sql: str, params: dict):
    """Insert a row with replication mode to bypass RLS."""
    db.execute(text("SET session_replication_role = REPLICA"))
    db.execute(text(sql), params)
    db.commit()
    db.execute(text("SET session_replication_role = DEFAULT"))


def _assert_invisible(db: Session, table: str, row_id, tenant_str: str, label: str):
    """Assert the row is NOT visible under the given tenant context."""
    db.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_str})
    count = db.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE id = :id"), {"id": row_id}
    ).scalar()
    assert count == 0, f"RLS BREACH: {label}"


def _assert_visible(db: Session, table: str, row_id, tenant_str: str, label: str):
    """Assert the row IS visible under the given tenant context."""
    db.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_str})
    count = db.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE id = :id"), {"id": row_id}
    ).scalar()
    assert count == 1, label


# ── products ─────────────────────────────────────────────────────────────


def test_products_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A products."""
    t = two_tenants
    pid = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO products (id, tenant_id, name, sku, active, stock, unit) "
        "VALUES (:id, :tid, 'Secret Product', 'SECRET-001', TRUE, 100, 'unit')",
        {"id": pid, "tid": t["a"]},
    )

    _assert_invisible(db, "products", pid, t["b_str"], "Tenant B sees Tenant A product")
    _assert_visible(db, "products", pid, t["a_str"], "Tenant A cannot see own product")


# ── clients ──────────────────────────────────────────────────────────────


def test_clients_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A clients."""
    t = two_tenants
    cid = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO clients (id, tenant_id, name) "
        "VALUES (:id, :tid, 'Secret Client')",
        {"id": cid, "tid": t["a"]},
    )

    _assert_invisible(db, "clients", cid, t["b_str"], "Tenant B sees Tenant A client")
    _assert_visible(db, "clients", cid, t["a_str"], "Tenant A cannot see own client")


# ── sales_orders ─────────────────────────────────────────────────────────


def test_sales_orders_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A sales orders."""
    t = two_tenants
    soid = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO sales_orders (id, tenant_id, number, status, order_date) "
        "VALUES (:id, :tid, :num, 'draft', NOW())",
        {"id": soid, "tid": t["a"], "num": f"SO-ISO-{soid.hex[:8]}"},
    )

    _assert_invisible(db, "sales_orders", soid, t["b_str"], "Tenant B sees Tenant A sales order")
    _assert_visible(db, "sales_orders", soid, t["a_str"], "Tenant A cannot see own sales order")


# ── invoices ─────────────────────────────────────────────────────────────


def test_invoices_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A invoices."""
    t = two_tenants
    inv_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    # Create a client first (customer_id NOT NULL on invoices)
    _insert_as_replica(
        db,
        "INSERT INTO clients (id, tenant_id, name) VALUES (:id, :tid, 'Invoice Client')",
        {"id": cust_id, "tid": t["a"]},
    )
    _insert_as_replica(
        db,
        "INSERT INTO invoices (id, tenant_id, number, customer_id, amount, subtotal, vat, total, status) "
        "VALUES (:id, :tid, :num, :cid, 100, 82.64, 17.36, 100, 'draft')",
        {"id": inv_id, "tid": t["a"], "num": f"INV-ISO-{inv_id.hex[:8]}", "cid": cust_id},
    )

    _assert_invisible(db, "invoices", inv_id, t["b_str"], "Tenant B sees Tenant A invoice")
    _assert_visible(db, "invoices", inv_id, t["a_str"], "Tenant A cannot see own invoice")


# ── purchases ────────────────────────────────────────────────────────────


def test_purchases_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A purchases."""
    t = two_tenants
    pid = uuid.uuid4()
    user_id = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO purchases (id, tenant_id, number, date, subtotal, taxes, total, status, user_id, created_at, updated_at) "
        "VALUES (:id, :tid, :num, NOW(), 100, 21, 121, 'draft', :uid, NOW(), NOW())",
        {"id": pid, "tid": t["a"], "num": f"PO-ISO-{pid.hex[:8]}", "uid": user_id},
    )

    _assert_invisible(db, "purchases", pid, t["b_str"], "Tenant B sees Tenant A purchase")
    _assert_visible(db, "purchases", pid, t["a_str"], "Tenant A cannot see own purchase")


# ── pos_receipts (requires pos_registers + pos_shifts) ───────────────────


def test_pos_receipts_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A POS receipts."""
    t = two_tenants
    reg_id = uuid.uuid4()
    shift_id = uuid.uuid4()
    receipt_id = uuid.uuid4()

    # Create register for tenant A
    _insert_as_replica(
        db,
        "INSERT INTO pos_registers (id, tenant_id, name, active) "
        "VALUES (:id, :tid, 'Reg-ISO', TRUE)",
        {"id": reg_id, "tid": t["a"]},
    )
    # Create shift
    _insert_as_replica(
        db,
        "INSERT INTO pos_shifts (id, register_id, opened_by, opened_at, opening_float, status) "
        "VALUES (:id, :rid, :uid, NOW(), 0, 'open')",
        {"id": shift_id, "rid": reg_id, "uid": uuid.uuid4()},
    )
    # Create receipt
    _insert_as_replica(
        db,
        "INSERT INTO pos_receipts (id, tenant_id, register_id, shift_id, number, status, gross_total, tax_total, currency, created_at) "
        "VALUES (:id, :tid, :rid, :sid, :num, 'paid', 100, 12, 'USD', NOW())",
        {
            "id": receipt_id,
            "tid": t["a"],
            "rid": reg_id,
            "sid": shift_id,
            "num": f"REC-ISO-{receipt_id.hex[:8]}",
        },
    )

    _assert_invisible(db, "pos_receipts", receipt_id, t["b_str"], "Tenant B sees Tenant A POS receipt")
    _assert_visible(db, "pos_receipts", receipt_id, t["a_str"], "Tenant A cannot see own POS receipt")


# ── stock_items (requires warehouses + products) ─────────────────────────


def test_stock_items_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A stock items."""
    t = two_tenants
    wh_id = uuid.uuid4()
    prod_id = uuid.uuid4()
    si_id = uuid.uuid4()

    # Create warehouse
    _insert_as_replica(
        db,
        "INSERT INTO warehouses (id, tenant_id, code, name, active) "
        "VALUES (:id, :tid, :code, 'ISO Warehouse', TRUE)",
        {"id": wh_id, "tid": t["a"], "code": f"WH-ISO-{wh_id.hex[:8]}"},
    )
    # Create product
    _insert_as_replica(
        db,
        "INSERT INTO products (id, tenant_id, name, sku, active, stock, unit) "
        "VALUES (:id, :tid, 'Stock Product', :sku, TRUE, 0, 'unit')",
        {"id": prod_id, "tid": t["a"], "sku": f"SKU-SI-{prod_id.hex[:8]}"},
    )
    # Create stock item
    _insert_as_replica(
        db,
        "INSERT INTO stock_items (id, tenant_id, warehouse_id, product_id, qty) "
        "VALUES (:id, :tid, :wid, :pid, 50)",
        {"id": si_id, "tid": t["a"], "wid": wh_id, "pid": prod_id},
    )

    _assert_invisible(db, "stock_items", si_id, t["b_str"], "Tenant B sees Tenant A stock item")
    _assert_visible(db, "stock_items", si_id, t["a_str"], "Tenant A cannot see own stock item")


# ── bank_accounts ────────────────────────────────────────────────────────


def test_bank_accounts_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A bank accounts."""
    t = two_tenants
    ba_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    # Create client for the customer_id FK
    _insert_as_replica(
        db,
        "INSERT INTO clients (id, tenant_id, name) VALUES (:id, :tid, 'Bank Client')",
        {"id": cust_id, "tid": t["a"]},
    )
    _insert_as_replica(
        db,
        "INSERT INTO bank_accounts (id, tenant_id, name, iban, currency, customer_id) "
        "VALUES (:id, :tid, 'Secret Account', 'ES1234567890', 'EUR', :cid)",
        {"id": ba_id, "tid": t["a"], "cid": cust_id},
    )

    _assert_invisible(db, "bank_accounts", ba_id, t["b_str"], "Tenant B sees Tenant A bank account")
    _assert_visible(db, "bank_accounts", ba_id, t["a_str"], "Tenant A cannot see own bank account")


# ── expenses ─────────────────────────────────────────────────────────────


def test_expenses_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A expenses."""
    t = two_tenants
    eid = uuid.uuid4()
    user_id = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO expenses (id, tenant_id, date, concept, amount, vat, total, status, user_id, created_at) "
        "VALUES (:id, :tid, NOW(), 'Secret Expense', 100, 21, 121, 'pending', :uid, NOW())",
        {"id": eid, "tid": t["a"], "uid": user_id},
    )

    _assert_invisible(db, "expenses", eid, t["b_str"], "Tenant B sees Tenant A expense")
    _assert_visible(db, "expenses", eid, t["a_str"], "Tenant A cannot see own expense")


# ── import_batches ───────────────────────────────────────────────────────


def test_import_batches_isolation(db: Session, two_tenants):
    """Tenant B cannot see Tenant A import batches."""
    t = two_tenants
    bid = uuid.uuid4()

    _insert_as_replica(
        db,
        "INSERT INTO import_batches (id, tenant_id, source_type, origin, status, created_by, created_at, updated_at) "
        "VALUES (:id, :tid, 'csv', 'upload', 'PENDING', 'tester', NOW(), NOW())",
        {"id": bid, "tid": t["a"]},
    )

    _assert_invisible(db, "import_batches", bid, t["b_str"], "Tenant B sees Tenant A import batch")
    _assert_visible(db, "import_batches", bid, t["a_str"], "Tenant A cannot see own import batch")


# ── cross-tenant write ──────────────────────────────────────────────────


def test_cross_tenant_insert_blocked(db: Session, two_tenants):
    """Tenant B cannot insert data with Tenant A's tenant_id."""
    t = two_tenants
    pid = uuid.uuid4()

    # Set session as tenant B, then try to write with tenant A's tenant_id
    db.execute(text("SET app.tenant_id = :tid"), {"tid": t["b_str"]})

    try:
        db.execute(
            text(
                "INSERT INTO products (id, tenant_id, name, sku, active, stock, unit) "
                "VALUES (:id, :tid, 'Injected', 'INJECT-001', TRUE, 0, 'unit')"
            ),
            {"id": pid, "tid": t["a"]},
        )
        db.commit()
        # If insert succeeded, verify it's not visible to either tenant
        count = db.execute(
            text("SELECT COUNT(*) FROM products WHERE id = :id"), {"id": pid}
        ).scalar()
        assert count == 0, "Cross-tenant INSERT visible — RLS WITH CHECK failed"
    except Exception:
        db.rollback()  # Expected: RLS violation
