"""Restaurant — CRUD endpoints for tables (mesas) and orders (comandas)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/restaurant",
    tags=["Restaurant"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    tid = claims.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    return UUID(str(tid))


# ---------------------------------------------------------------------------
# Schemas — Tables
# ---------------------------------------------------------------------------


class TableCreateIn(BaseModel):
    number: int
    name: str | None = Field(default=None, max_length=50)
    capacity: int = 4
    zone: str | None = Field(default=None, max_length=50)
    sort_order: int = 0


class TableUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    capacity: int | None = None
    zone: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    sort_order: int | None = None


# ---------------------------------------------------------------------------
# Schemas — Orders
# ---------------------------------------------------------------------------


class OrderCreateIn(BaseModel):
    table_id: UUID
    waiter_id: UUID | None = None
    waiter_name: str | None = Field(default=None, max_length=100)
    guests: int = 1
    notes: str | None = None


class OrderItemCreateIn(BaseModel):
    product_id: UUID
    product_name: str = Field(max_length=200)
    qty: float = 1
    unit_price: float
    notes: str | None = None


class OrderItemUpdateIn(BaseModel):
    qty: float | None = None
    notes: str | None = None
    status: str | None = Field(default=None, max_length=20)


# ===========================================================================
# TABLES endpoints
# ===========================================================================


@router.get("/tables", response_model=list[dict[str, Any]])
def list_tables(
    request: Request,
    zone: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista todas las mesas del tenant."""
    ensure_guc_from_request(request, db, persist=True)

    clauses = ["is_active = true"]
    params: dict[str, Any] = {}

    if zone:
        clauses.append("zone = :zone")
        params["zone"] = zone
    if status:
        clauses.append("status = :status")
        params["status"] = status

    where = " AND ".join(clauses)
    rows = db.execute(
        text(
            "SELECT id, number, name, capacity, zone, status, is_active, sort_order, created_at "
            f"FROM restaurant_tables WHERE {where} "
            "ORDER BY sort_order, number"
        ),
        params,
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "number": r[1],
            "name": r[2],
            "capacity": r[3],
            "zone": r[4],
            "status": r[5],
            "is_active": r[6],
            "sort_order": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


@router.post("/tables", response_model=dict[str, Any], status_code=201)
def create_table(payload: TableCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva mesa."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    existing = db.execute(
        text(
            "SELECT id FROM restaurant_tables WHERE tenant_id = :tid AND number = :num"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id, "num": payload.number},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="table_number_already_exists")

    row = db.execute(
        text(
            "INSERT INTO restaurant_tables(tenant_id, number, name, capacity, zone, sort_order) "
            "VALUES (:tid, :number, :name, :capacity, :zone, :sort_order) "
            "RETURNING id, created_at"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {
            "tid": tenant_id,
            "number": payload.number,
            "name": payload.name,
            "capacity": payload.capacity,
            "zone": payload.zone,
            "sort_order": payload.sort_order,
        },
    ).first()

    db.commit()

    return {
        "id": str(row[0]),
        "number": payload.number,
        "name": payload.name,
        "capacity": payload.capacity,
        "zone": payload.zone,
        "created_at": row[1].isoformat() if row[1] else None,
    }


@router.put("/tables/{table_id}", response_model=dict[str, Any])
def update_table(
    table_id: str, payload: TableUpdateIn, request: Request, db: Session = Depends(get_db)
):
    """Actualiza una mesa (incluye cambios de estado)."""
    ensure_guc_from_request(request, db, persist=True)

    existing = db.execute(
        text("SELECT id FROM restaurant_tables WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": table_id},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="table_not_found")

    updates: list[str] = []
    params: dict[str, Any] = {"tid": table_id}

    if payload.name is not None:
        updates.append("name = :name")
        params["name"] = payload.name
    if payload.capacity is not None:
        updates.append("capacity = :capacity")
        params["capacity"] = payload.capacity
    if payload.zone is not None:
        updates.append("zone = :zone")
        params["zone"] = payload.zone
    if payload.status is not None:
        updates.append("status = :status")
        params["status"] = payload.status
    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = payload.is_active
    if payload.sort_order is not None:
        updates.append("sort_order = :sort_order")
        params["sort_order"] = payload.sort_order

    if not updates:
        raise HTTPException(status_code=400, detail="no_fields_to_update")

    db.execute(
        text(f"UPDATE restaurant_tables SET {', '.join(updates)} WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        params,
    )
    db.commit()

    return {"id": table_id, "status": "updated"}


@router.delete("/tables/{table_id}", response_model=dict[str, Any])
def deactivate_table(table_id: str, request: Request, db: Session = Depends(get_db)):
    """Desactiva una mesa (soft-delete)."""
    ensure_guc_from_request(request, db, persist=True)

    existing = db.execute(
        text("SELECT id FROM restaurant_tables WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": table_id},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="table_not_found")

    db.execute(
        text("UPDATE restaurant_tables SET is_active = false WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": table_id},
    )
    db.commit()

    return {"id": table_id, "status": "deactivated"}


# ===========================================================================
# ORDERS (Comandas) endpoints
# ===========================================================================


@router.get("/orders", response_model=list[dict[str, Any]])
def list_orders(
    request: Request,
    status: str | None = Query(default=None),
    table_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista las comandas del tenant."""
    ensure_guc_from_request(request, db, persist=True)

    clauses: list[str] = []
    params: dict[str, Any] = {}

    if status:
        clauses.append("o.status = :status")
        params["status"] = status
    if table_id:
        clauses.append("o.table_id = :table_id")
        params["table_id"] = table_id

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    rows = db.execute(
        text(
            "SELECT o.id, o.order_number, o.table_id, t.number AS table_number, t.name AS table_name, "
            "o.waiter_name, o.status, o.guests, o.subtotal, o.tax_total, o.total, "
            "o.opened_at, o.closed_at "
            "FROM restaurant_orders o "
            "JOIN restaurant_tables t ON t.id = o.table_id "
            f"{where} "
            "ORDER BY o.opened_at DESC"
        ),
        params,
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "order_number": r[1],
            "table_id": str(r[2]),
            "table_number": r[3],
            "table_name": r[4],
            "waiter_name": r[5],
            "status": r[6],
            "guests": r[7],
            "subtotal": float(r[8]) if r[8] else 0,
            "tax_total": float(r[9]) if r[9] else 0,
            "total": float(r[10]) if r[10] else 0,
            "opened_at": r[11].isoformat() if r[11] else None,
            "closed_at": r[12].isoformat() if r[12] else None,
        }
        for r in rows
    ]


@router.post("/orders", response_model=dict[str, Any], status_code=201)
def create_order(payload: OrderCreateIn, request: Request, db: Session = Depends(get_db)):
    """Abre una nueva comanda para una mesa (la mesa pasa a 'occupied')."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    table = db.execute(
        text(
            "SELECT id, status FROM restaurant_tables WHERE id = :tid AND is_active = true"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": str(payload.table_id)},
    ).first()
    if not table:
        raise HTTPException(status_code=404, detail="table_not_found")

    # Generate order number
    seq = db.execute(
        text(
            "SELECT COALESCE(MAX(CAST(SUBSTRING(order_number FROM '[0-9]+') AS INTEGER)), 0) + 1 "
            "FROM restaurant_orders WHERE tenant_id = :tid"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).scalar()
    order_number = f"CMD-{seq:06d}"

    row = db.execute(
        text(
            "INSERT INTO restaurant_orders(tenant_id, table_id, order_number, waiter_id, waiter_name, guests, notes) "
            "VALUES (:tid, :table_id, :order_number, :waiter_id, :waiter_name, :guests, :notes) "
            "RETURNING id, opened_at"
        ).bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True)),
            bindparam("table_id", type_=PGUUID(as_uuid=True)),
            bindparam("waiter_id", type_=PGUUID(as_uuid=True)),
        ),
        {
            "tid": tenant_id,
            "table_id": str(payload.table_id),
            "order_number": order_number,
            "waiter_id": str(payload.waiter_id) if payload.waiter_id else None,
            "waiter_name": payload.waiter_name,
            "guests": payload.guests,
            "notes": payload.notes,
        },
    ).first()

    # Set table to occupied
    db.execute(
        text("UPDATE restaurant_tables SET status = 'occupied' WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": str(payload.table_id)},
    )

    db.commit()

    return {
        "id": str(row[0]),
        "order_number": order_number,
        "table_id": str(payload.table_id),
        "opened_at": row[1].isoformat() if row[1] else None,
    }


@router.get("/orders/{order_id}", response_model=dict[str, Any])
def get_order(order_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene una comanda con sus ítems."""
    ensure_guc_from_request(request, db, persist=True)

    order = db.execute(
        text(
            "SELECT o.id, o.order_number, o.table_id, t.number AS table_number, t.name AS table_name, "
            "o.waiter_id, o.waiter_name, o.status, o.guests, o.notes, "
            "o.subtotal, o.tax_total, o.total, o.opened_at, o.closed_at "
            "FROM restaurant_orders o "
            "JOIN restaurant_tables t ON t.id = o.table_id "
            "WHERE o.id = :oid"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id},
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    items = db.execute(
        text(
            "SELECT id, product_id, product_name, qty, unit_price, line_total, notes, status, "
            "sent_to_kitchen_at, ready_at, created_at "
            "FROM restaurant_order_items WHERE order_id = :oid "
            "ORDER BY created_at"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id},
    ).fetchall()

    return {
        "id": str(order[0]),
        "order_number": order[1],
        "table_id": str(order[2]),
        "table_number": order[3],
        "table_name": order[4],
        "waiter_id": str(order[5]) if order[5] else None,
        "waiter_name": order[6],
        "status": order[7],
        "guests": order[8],
        "notes": order[9],
        "subtotal": float(order[10]) if order[10] else 0,
        "tax_total": float(order[11]) if order[11] else 0,
        "total": float(order[12]) if order[12] else 0,
        "opened_at": order[13].isoformat() if order[13] else None,
        "closed_at": order[14].isoformat() if order[14] else None,
        "items": [
            {
                "id": str(i[0]),
                "product_id": str(i[1]),
                "product_name": i[2],
                "qty": float(i[3]),
                "unit_price": float(i[4]),
                "line_total": float(i[5]),
                "notes": i[6],
                "status": i[7],
                "sent_to_kitchen_at": i[8].isoformat() if i[8] else None,
                "ready_at": i[9].isoformat() if i[9] else None,
                "created_at": i[10].isoformat() if i[10] else None,
            }
            for i in items
        ],
    }


@router.post("/orders/{order_id}/items", response_model=dict[str, Any], status_code=201)
def add_order_item(
    order_id: str, payload: OrderItemCreateIn, request: Request, db: Session = Depends(get_db)
):
    """Agrega un ítem a la comanda."""
    ensure_guc_from_request(request, db, persist=True)

    order = db.execute(
        text("SELECT id, status FROM restaurant_orders WHERE id = :oid").bindparams(
            bindparam("oid", type_=PGUUID(as_uuid=True))
        ),
        {"oid": order_id},
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    if order[1] in ("paid", "canceled"):
        raise HTTPException(status_code=400, detail="order_is_closed")

    line_total = round(payload.qty * payload.unit_price, 2)

    row = db.execute(
        text(
            "INSERT INTO restaurant_order_items(order_id, product_id, product_name, qty, unit_price, line_total, notes) "
            "VALUES (:oid, :product_id, :product_name, :qty, :unit_price, :line_total, :notes) "
            "RETURNING id, created_at"
        ).bindparams(
            bindparam("oid", type_=PGUUID(as_uuid=True)),
            bindparam("product_id", type_=PGUUID(as_uuid=True)),
        ),
        {
            "oid": order_id,
            "product_id": str(payload.product_id),
            "product_name": payload.product_name,
            "qty": payload.qty,
            "unit_price": payload.unit_price,
            "line_total": line_total,
            "notes": payload.notes,
        },
    ).first()

    # Recalculate order totals
    _recalculate_order_totals(db, order_id)
    db.commit()

    return {
        "id": str(row[0]),
        "order_id": order_id,
        "product_name": payload.product_name,
        "qty": payload.qty,
        "line_total": line_total,
        "created_at": row[1].isoformat() if row[1] else None,
    }


@router.put("/orders/{order_id}/items/{item_id}", response_model=dict[str, Any])
def update_order_item(
    order_id: str,
    item_id: str,
    payload: OrderItemUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Actualiza un ítem de la comanda (qty, notes, status)."""
    ensure_guc_from_request(request, db, persist=True)

    item = db.execute(
        text(
            "SELECT id, unit_price FROM restaurant_order_items WHERE id = :iid AND order_id = :oid"
        ).bindparams(
            bindparam("iid", type_=PGUUID(as_uuid=True)),
            bindparam("oid", type_=PGUUID(as_uuid=True)),
        ),
        {"iid": item_id, "oid": order_id},
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    updates: list[str] = []
    params: dict[str, Any] = {"iid": item_id}

    if payload.qty is not None:
        updates.append("qty = :qty")
        params["qty"] = payload.qty
        line_total = round(payload.qty * float(item[1]), 2)
        updates.append("line_total = :line_total")
        params["line_total"] = line_total
    if payload.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = payload.notes
    if payload.status is not None:
        updates.append("status = :status")
        params["status"] = payload.status

    if not updates:
        raise HTTPException(status_code=400, detail="no_fields_to_update")

    db.execute(
        text(f"UPDATE restaurant_order_items SET {', '.join(updates)} WHERE id = :iid").bindparams(
            bindparam("iid", type_=PGUUID(as_uuid=True))
        ),
        params,
    )

    _recalculate_order_totals(db, order_id)
    db.commit()

    return {"id": item_id, "order_id": order_id, "status": "updated"}


@router.delete("/orders/{order_id}/items/{item_id}", response_model=dict[str, Any])
def remove_order_item(order_id: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina un ítem de la comanda."""
    ensure_guc_from_request(request, db, persist=True)

    item = db.execute(
        text(
            "SELECT id FROM restaurant_order_items WHERE id = :iid AND order_id = :oid"
        ).bindparams(
            bindparam("iid", type_=PGUUID(as_uuid=True)),
            bindparam("oid", type_=PGUUID(as_uuid=True)),
        ),
        {"iid": item_id, "oid": order_id},
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    db.execute(
        text("DELETE FROM restaurant_order_items WHERE id = :iid").bindparams(
            bindparam("iid", type_=PGUUID(as_uuid=True))
        ),
        {"iid": item_id},
    )

    _recalculate_order_totals(db, order_id)
    db.commit()

    return {"id": item_id, "order_id": order_id, "status": "removed"}


@router.post("/orders/{order_id}/send-kitchen", response_model=dict[str, Any])
def send_to_kitchen(order_id: str, request: Request, db: Session = Depends(get_db)):
    """Envía los ítems pendientes a cocina (status → 'preparing')."""
    ensure_guc_from_request(request, db, persist=True)

    order = db.execute(
        text("SELECT id, status FROM restaurant_orders WHERE id = :oid").bindparams(
            bindparam("oid", type_=PGUUID(as_uuid=True))
        ),
        {"oid": order_id},
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    if order[1] in ("paid", "canceled"):
        raise HTTPException(status_code=400, detail="order_is_closed")

    now = datetime.now(UTC)

    result = db.execute(
        text(
            "UPDATE restaurant_order_items "
            "SET status = 'preparing', sent_to_kitchen_at = :now "
            "WHERE order_id = :oid AND status = 'pending'"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id, "now": now},
    )

    # Update order status to preparing
    db.execute(
        text(
            "UPDATE restaurant_orders SET status = 'preparing', updated_at = :now WHERE id = :oid"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id, "now": now},
    )

    db.commit()

    return {"order_id": order_id, "items_sent": result.rowcount}


@router.post("/orders/{order_id}/close", response_model=dict[str, Any])
def close_order(order_id: str, request: Request, db: Session = Depends(get_db)):
    """Cierra una comanda (calcula totales, mesa pasa a 'cleaning')."""
    ensure_guc_from_request(request, db, persist=True)
    raise HTTPException(
        status_code=501,
        detail="restaurant_close_requires_pos_billing_integration",
    )

    order = db.execute(
        text("SELECT id, table_id, status FROM restaurant_orders WHERE id = :oid").bindparams(
            bindparam("oid", type_=PGUUID(as_uuid=True))
        ),
        {"oid": order_id},
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    if order[2] in ("paid", "canceled"):
        raise HTTPException(status_code=400, detail="order_already_closed")

    now = datetime.now(UTC)

    # Recalculate totals
    totals = _recalculate_order_totals(db, order_id)

    # Close the order
    db.execute(
        text(
            "UPDATE restaurant_orders SET status = 'paid', closed_at = :now, updated_at = :now "
            "WHERE id = :oid"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id, "now": now},
    )

    # Set table to cleaning
    table_id = str(order[1])
    db.execute(
        text("UPDATE restaurant_tables SET status = 'cleaning' WHERE id = :tid").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": table_id},
    )

    db.commit()

    return {
        "order_id": order_id,
        "status": "paid",
        "subtotal": totals["subtotal"],
        "tax_total": totals["tax_total"],
        "total": totals["total"],
        "closed_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _recalculate_order_totals(db: Session, order_id: str) -> dict[str, float]:
    """Recalcula subtotal/total de la comanda a partir de sus ítems activos."""
    row = db.execute(
        text(
            "SELECT COALESCE(SUM(line_total), 0) "
            "FROM restaurant_order_items "
            "WHERE order_id = :oid AND status != 'canceled'"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id},
    ).first()

    subtotal = float(row[0]) if row else 0
    tax_total = 0.0
    total = subtotal + tax_total

    db.execute(
        text(
            "UPDATE restaurant_orders "
            "SET subtotal = :subtotal, tax_total = :tax_total, total = :total, updated_at = NOW() "
            "WHERE id = :oid"
        ).bindparams(bindparam("oid", type_=PGUUID(as_uuid=True))),
        {"oid": order_id, "subtotal": subtotal, "tax_total": tax_total, "total": total},
    )

    return {"subtotal": subtotal, "tax_total": tax_total, "total": total}
