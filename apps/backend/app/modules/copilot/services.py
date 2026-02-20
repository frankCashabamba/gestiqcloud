from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def _mask_email(val: str | None) -> str | None:
    if not val or "@" not in val:
        return val
    name, dom = val.split("@", 1)
    if len(name) <= 2:
        return "*" * len(name) + "@" + dom
    return name[0] + "*" * (len(name) - 2) + name[-1] + "@" + dom


def _mask_phone(val: str | None) -> str | None:
    if not val:
        return val
    digits = [c for c in val if c.isdigit()]
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + "".join(digits[-4:])


def pii_mask_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for k in list(out.keys()):
        lk = k.lower()
        if lk in ("email", "correo"):
            out[k] = _mask_email(str(out[k]) if out[k] is not None else None)
        elif lk in ("telefono", "phone"):
            out[k] = _mask_phone(str(out[k]) if out[k] is not None else None)
        elif lk in ("identificacion", "dni", "nif", "vat"):
            v = str(out[k]) if out[k] is not None else None
            if v:
                out[k] = v[:2] + "*" * max(0, len(v) - 4) + v[-2:]
    return out


def _fetch_all(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    res = db.execute(text(sql), params)
    cols = list(res.keys())
    rows = [dict(zip(cols, r, strict=False)) for r in res.fetchall()]
    return rows


def _table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table
            """
        ),
        {"table": table_name},
    ).fetchall()
    return {str(r[0]).lower() for r in rows}


def _pick_column(columns: set[str], *candidates: str) -> str | None:
    for c in candidates:
        if c.lower() in columns:
            return c
    return None


def _safe_topic(title: str, sql: str, fn) -> dict[str, Any]:
    try:
        rows = fn()
        return {"cards": [{"title": title, "data": rows}], "sql": sql}
    except SQLAlchemyError as e:
        return {
            "cards": [{"title": title, "data": []}],
            "sql": sql,
            "note": f"topic_unavailable:{type(e).__name__}",
        }


def query_readonly(db: Session, topic: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params or {}
    # Only allow curated read-only queries (RLS enforced by DB)
    if topic == "ventas_mes":
        sql = (
            "SELECT date_trunc('month', so.created_at)::date AS mes, count(*) AS pedidos "
            "FROM sales_orders so GROUP BY 1 ORDER BY 1 DESC LIMIT 12"
        )
        rows = _fetch_all(db, sql, {})
        return {"cards": [{"title": "Pedidos por mes", "series": rows}], "sql": sql}

    if topic == "ventas_por_almacen":
        sql = (
            "SELECT w.code AS almacen, sum(sm.qty) AS unidades "
            "FROM stock_moves sm JOIN warehouses w ON w.id=sm.warehouse_id "
            "WHERE sm.kind='issue' GROUP BY 1 ORDER BY 2 DESC"
        )
        rows = _fetch_all(db, sql, {})
        return {"cards": [{"title": "Salidas por almacén", "data": rows}], "sql": sql}

    if topic == "top_productos":
        cols = _table_columns(db, "sales_order_items")
        qty_col = _pick_column(cols, "quantity", "qty", "cantidad")
        price_col = _pick_column(cols, "unit_price", "price", "precio_unitario")
        if not qty_col or not price_col:
            return {
                "cards": [{"title": "Top productos", "data": []}],
                "sql": None,
                "note": "topic_unavailable:sales_order_items_columns",
            }
        sql = (
            f"SELECT p.id, p.name, sum(soi.{qty_col}) AS uds, "
            f"sum(soi.{qty_col}*soi.{price_col}) AS importe "
            "FROM sales_order_items soi JOIN products p ON p.id=soi.product_id "
            "GROUP BY 1,2 ORDER BY importe DESC NULLS LAST LIMIT 10"
        )
        return _safe_topic("Top productos", sql, lambda: _fetch_all(db, sql, {}))

    if topic == "stock_bajo":
        threshold = float(p.get("threshold", 5))
        sql = (
            "SELECT w.code AS almacen, si.product_id, si.qty FROM stock_items si "
            "JOIN warehouses w ON w.id=si.warehouse_id WHERE si.qty < :th ORDER BY si.qty ASC LIMIT 50"
        )
        rows = _fetch_all(db, sql, {"th": threshold})
        return {"cards": [{"title": "Stock bajo", "data": rows}], "sql": sql}

    if topic == "pendientes_sri_sii":
        sql_sri = (
            "SELECT count(*) AS pendientes FROM sri_submissions WHERE status NOT IN ('AUTHORIZED')"
        )
        sql_sii = "SELECT count(*) AS pendientes FROM sii_batches WHERE status NOT IN ('ACCEPTED')"
        sri = _fetch_all(db, sql_sri, {})
        sii = _fetch_all(db, sql_sii, {})
        return {
            "cards": [
                {"title": "SRI pendientes", "data": sri},
                {"title": "SII pendientes", "data": sii},
            ],
            "sql": sql_sri + ";" + sql_sii,
        }

    if topic == "cobros_pagos":
        cols = _table_columns(db, "bank_transactions")
        type_col = _pick_column(cols, "type", "tipo")
        status_col = _pick_column(cols, "status", "estado")
        amount_col = _pick_column(cols, "amount", "importe", "monto")
        if not type_col or not status_col or not amount_col:
            return {
                "cards": [{"title": "Cobros/Pagos", "data": []}],
                "sql": None,
                "note": "topic_unavailable:bank_transactions_columns",
            }
        sql = (
            f"SELECT {type_col}::text AS tipo, {status_col}::text AS estado, "
            f"count(*) AS n, sum({amount_col}) AS importe "
            "FROM bank_transactions GROUP BY 1,2 ORDER BY 4 DESC NULLS LAST"
        )
        return _safe_topic("Cobros/Pagos", sql, lambda: _fetch_all(db, sql, {}))

    # Default: unsupported
    return {"cards": [], "sql": None, "note": "topic_unsupported"}


def create_invoice_draft(
    db: Session, tenant_empresa_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    # Create a minimal draft invoice; never post
    proveedor = str(payload.get("proveedor") or "N/A")
    cliente_id = payload.get("cliente_id")
    subtotal = float(payload.get("subtotal") or 0)
    iva = float(payload.get("iva") or 0)
    total = float(payload.get("total") or (subtotal + iva))
    row = db.execute(
        text(
            """
            INSERT INTO facturas (numero, proveedor, fecha_emision, monto, estado, tenant_id, cliente_id, subtotal, iva, total)
            VALUES ('DRAFT', :prov, now()::date, :total, 'borrador', :emp, :cli, :sub, :iva, :tot)
            RETURNING id
            """
        ),
        {
            "prov": proveedor,
            "emp": int(tenant_empresa_id),
            "cli": cliente_id,
            "sub": subtotal,
            "iva": iva,
            "tot": total,
        },
    ).first()
    assert row is not None
    return {"id": int(row[0]), "status": "draft"}


def create_order_draft(
    db: Session, payload: dict[str, Any], tenant_id: str | None = None
) -> dict[str, Any]:
    cur = db.execute(
        text(
            "INSERT INTO sales_orders(customer_id, status, created_at) VALUES (:cid, 'draft', now()) RETURNING id"
        ),
        {"cid": payload.get("customer_id")},
    )
    oid = cur.scalar()
    assert oid is not None
    items = payload.get("items") or []
    for it in items:
        db.execute(
            text(
                "INSERT INTO sales_order_items(order_id, product_id, qty, unit_price) VALUES (:oid, :pid, :qty, :price)"
            ),
            {
                "oid": oid,
                "pid": it.get("product_id"),
                "qty": float(it.get("qty") or 0),
                "price": float(it.get("unit_price") or 0),
            },
        )
    return {"id": int(oid), "status": "draft"}


def create_transfer_draft(
    db: Session, payload: dict[str, Any], tenant_id: str | None = None
) -> dict[str, Any]:
    # Draft transfer: two stock_move tentative rows (no stock_items update)
    src = int(payload.get("from_warehouse_id") or 0)
    dst = int(payload.get("to_warehouse_id") or 0)
    prod = int(payload.get("product_id") or 0)
    qty = float(payload.get("qty") or 0)
    for wh, kind in ((src, "issue"), (dst, "receipt")):
        db.execute(
            text(
                "INSERT INTO stock_moves(product_id, warehouse_id, qty, kind, tentative, ref_type) VALUES (:pid, :wid, :q, :k, true, 'transfer_draft')"
            ),
            {"pid": prod, "wid": wh, "q": qty, "k": kind},
        )
    return {"status": "draft_transfer"}


def suggest_overlay_fields(db: Session) -> dict[str, Any]:
    # Simple heuristic suggestion based on products/clients columns
    # Returns a safe overlay proposal within limits
    overlay = {
        "ui": {
            "products": {
                "columns": ["sku", "name", "price"],
                "order": ["sku", "name"],
            },
            "clients": {
                "columns": ["nombre", "email"],
            },
        }
    }
    return overlay
