from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.rls import tenant_id_sql_expr


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


def pii_mask_row(row: Dict[str, Any]) -> Dict[str, Any]:
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


def _fetch_all(db: Session, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    res = db.execute(text(sql), params)
    cols = [c for c in res.keys()]
    rows = [dict(zip(cols, r)) for r in res.fetchall()]
    return rows


def query_readonly(db: Session, topic: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
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
        sql = (
            "SELECT p.id, p.name, sum(soi.qty) AS uds, sum(soi.qty*soi.unit_price) AS importe "
            "FROM sales_order_items soi JOIN products p ON p.id=soi.product_id "
            "GROUP BY 1,2 ORDER BY importe DESC NULLS LAST LIMIT 10"
        )
        rows = _fetch_all(db, sql, {})
        return {"cards": [{"title": "Top productos", "data": rows}], "sql": sql}

    if topic == "stock_bajo":
        threshold = float(p.get("threshold", 5))
        sql = (
            "SELECT w.code AS almacen, si.product_id, si.qty FROM stock_items si "
            "JOIN warehouses w ON w.id=si.warehouse_id WHERE si.qty < :th ORDER BY si.qty ASC LIMIT 50"
        )
        rows = _fetch_all(db, sql, {"th": threshold})
        return {"cards": [{"title": "Stock bajo", "data": rows}], "sql": sql}

    if topic == "pendientes_sri_sii":
        sql_sri = "SELECT count(*) AS pendientes FROM sri_submissions WHERE status NOT IN ('AUTHORIZED')"
        sql_sii = "SELECT count(*) AS pendientes FROM sii_batches WHERE status NOT IN ('ACCEPTED')"
        sri = _fetch_all(db, sql_sri, {})
        sii = _fetch_all(db, sql_sii, {})
        return {"cards": [{"title": "SRI pendientes", "data": sri}, {"title": "SII pendientes", "data": sii}], "sql": sql_sri + ";" + sql_sii}

    if topic == "cobros_pagos":
        sql = (
            "SELECT tipo::text AS tipo, estado::text AS estado, count(*) AS n, sum(importe) AS importe "
            "FROM bank_transactions GROUP BY 1,2 ORDER BY 4 DESC NULLS LAST"
        )
        rows = _fetch_all(db, sql, {})
        return {"cards": [{"title": "Cobros/Pagos", "data": rows}], "sql": sql}

    # Default: unsupported
    return {"cards": [], "sql": None, "note": "topic_unsupported"}


def create_invoice_draft(db: Session, tenant_empresa_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    # Create a minimal draft invoice; never post
    proveedor = str(payload.get("proveedor") or "N/A")
    cliente_id = payload.get("cliente_id")
    subtotal = float(payload.get("subtotal") or 0)
    iva = float(payload.get("iva") or 0)
    total = float(payload.get("total") or (subtotal + iva))
    row = db.execute(
        text(
            """
            INSERT INTO facturas (numero, proveedor, fecha_emision, monto, estado, empresa_id, cliente_id, subtotal, iva, total)
            VALUES ('DRAFT', :prov, now()::date, :total, 'borrador', :emp, :cli, :sub, :iva, :tot)
            RETURNING id
            """
        ),
        {"prov": proveedor, "emp": int(tenant_empresa_id), "cli": cliente_id, "sub": subtotal, "iva": iva, "tot": total},
    ).first()
    return {"id": int(row[0]), "status": "draft"}


def create_order_draft(db: Session, payload: Dict[str, Any], tenant_id: str | None = None) -> Dict[str, Any]:
    cur = db.execute(
        text(
            "INSERT INTO sales_orders(customer_id, status, created_at) VALUES (:cid, 'draft', now()) RETURNING id"
        ),
        {"cid": payload.get("customer_id")},
    )
    oid = cur.scalar()
    items = payload.get("items") or []
    for it in items:
        db.execute(
            text(
                "INSERT INTO sales_order_items(order_id, product_id, qty, unit_price) VALUES (:oid, :pid, :qty, :price)"
            ),
            {"oid": oid, "pid": it.get("product_id"), "qty": float(it.get("qty") or 0), "price": float(it.get("unit_price") or 0)},
        )
    return {"id": int(oid), "status": "draft"}


def create_transfer_draft(db: Session, payload: Dict[str, Any], tenant_id: str | None = None) -> Dict[str, Any]:
    # Draft transfer: two stock_move tentative rows (no stock_items update)
    src = int(payload.get("from_warehouse_id"))
    dst = int(payload.get("to_warehouse_id"))
    prod = int(payload.get("product_id"))
    qty = float(payload.get("qty") or 0)
    for wh, kind in ((src, "issue"), (dst, "receipt")):
        db.execute(
            text(
                "INSERT INTO stock_moves(product_id, warehouse_id, qty, kind, tentative, ref_type) VALUES (:pid, :wid, :q, :k, true, 'transfer_draft')"
            ),
            {"pid": prod, "wid": wh, "q": qty, "k": kind},
        )
    return {"status": "draft_transfer"}


def suggest_overlay_fields(db: Session) -> Dict[str, Any]:
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
