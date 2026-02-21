from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.ai.service import AIService
from app.services.ai.base import AITask

logger = logging.getLogger(__name__)


def _tenant_where(alias: str | None = None) -> str:
    col = f"{alias}.tenant_id" if alias else "tenant_id"
    return f"CAST({col}::text AS uuid) = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


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


def _safe_topic(db: Session, title: str, sql: str, fn) -> dict[str, Any]:
    try:
        rows = fn()
        return {"cards": [{"title": title, "data": rows}], "sql": sql}
    except SQLAlchemyError as e:
        # Ensure the session is usable after a failed statement.
        db.rollback()
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
            f"FROM sales_orders so WHERE {_tenant_where('so')} "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 12"
        )
        rows = _fetch_all(db, sql, {})
        return {"cards": [{"title": "Pedidos por mes", "series": rows}], "sql": sql}

    if topic == "ventas_por_almacen":
        sql = (
            "SELECT w.code AS almacen, sum(sm.qty) AS unidades "
            "FROM stock_moves sm JOIN warehouses w ON w.id=sm.warehouse_id "
            f"WHERE {_tenant_where('sm')} AND sm.kind='issue' GROUP BY 1 ORDER BY 2 DESC"
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
            f"WHERE {_tenant_where('soi')} "
            "GROUP BY 1,2 ORDER BY importe DESC NULLS LAST LIMIT 10"
        )
        return _safe_topic(db, "Top productos", sql, lambda: _fetch_all(db, sql, {}))

    if topic == "stock_bajo":
        threshold = float(p.get("threshold", 5))
        sql = (
            "SELECT w.code AS almacen, si.product_id, si.qty FROM stock_items si "
            f"JOIN warehouses w ON w.id=si.warehouse_id WHERE {_tenant_where('si')} AND si.qty < :th ORDER BY si.qty ASC LIMIT 50"
        )
        rows = _fetch_all(db, sql, {"th": threshold})
        return {"cards": [{"title": "Stock bajo", "data": rows}], "sql": sql}

    if topic == "pendientes_sri_sii":
        sql_sri = (
            f"SELECT count(*) AS pendientes FROM sri_submissions WHERE {_tenant_where()} AND status NOT IN ('AUTHORIZED')"
        )
        sql_sii = (
            f"SELECT count(*) AS pendientes FROM sii_batches WHERE {_tenant_where()} AND status NOT IN ('ACCEPTED')"
        )
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
            f"FROM bank_transactions WHERE {_tenant_where()} GROUP BY 1,2 ORDER BY 4 DESC NULLS LAST"
        )
        return _safe_topic(db, "Cobros/Pagos", sql, lambda: _fetch_all(db, sql, {}))

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


async def query_readonly_enhanced(
    db: Session,
    topic: str,
    params: dict[str, Any] | None = None,
    with_ai_insights: bool = True,
) -> dict[str, Any]:
    """Query curada + análisis IA opcional (insights inteligentes)"""
    p = params or {}

    # 1. Obtener datos base (igual que query_readonly)
    result = query_readonly(db, topic, p)

    # 2. Si no hay datos, retornar sin análisis
    if not result.get("cards") or not result["cards"][0].get("data"):
        return result

    # 3. Mejorar con IA si se solicita
    if with_ai_insights:
        try:
            # UUID/Decimal/datetime can appear in DB rows; stringify non-JSON-native values.
            summary = json.dumps(result["cards"], indent=2, ensure_ascii=False, default=str)
            topic_display = topic.replace("_", " ").title()

            # Limit data sent to AI to avoid long prompts
            cards_data = result["cards"][0]["data"][:10]
            summary = json.dumps(cards_data, ensure_ascii=False, default=str)

            ai_response = await AIService.query(
                task=AITask.ANALYSIS,
                prompt=f"""Datos de {topic_display}: {summary}
Responde SOLO con JSON: {{"findings":["..."],"recommendations":["..."]}}""",
                temperature=0.3,
                max_tokens=250,
            )

            if not ai_response.is_error:
                try:
                    insights = json.loads(ai_response.content)
                    result["ai_insights"] = insights
                    result["ai_model"] = ai_response.model
                except json.JSONDecodeError:
                    logger.debug(f"JSON parse error in AI response: {ai_response.content}")
                    result["ai_insights"] = {"raw": ai_response.content}
                    result["ai_model"] = ai_response.model
            else:
                logger.warning(f"AI analysis failed for {topic}: {ai_response.error}")

        except Exception as e:
            logger.error(f"Error in query_readonly_enhanced: {e}", exc_info=True)
            # Continue sin insights si falla IA

    return result


async def get_smart_suggestions(db: Session) -> list[dict[str, Any]]:
    """Genera sugerencias contextuales inteligentes usando IA"""
    suggestions = []

    try:
        # 1. Stock bajo - con sugerencia de acción
        low_stock = query_readonly(db, "stock_bajo", {"threshold": 5})
        if low_stock["cards"][0]["data"]:
            items_count = len(low_stock["cards"][0]["data"])
            context = f"Hay {items_count} productos con stock bajo"

            suggestion_text = await AIService.generate_suggestion(
                context=context, suggestion_type="inventory"
            )
            if suggestion_text:
                suggestions.append(
                    {
                        "type": "inventory",
                        "priority": "high" if items_count > 3 else "medium",
                        "content": suggestion_text,
                        "action": "review_stock",
                        "count": items_count,
                    }
                )

    except Exception as e:
        if isinstance(e, SQLAlchemyError):
            db.rollback()
        logger.warning(f"Error generating inventory suggestions: {e}")

    try:
        # 2. Oportunidades de venta cruzada
        top_products = query_readonly(db, "top_productos", {})
        if top_products["cards"][0]["data"]:
            top_5 = top_products["cards"][0]["data"][:5]
            product_names = ", ".join(p.get("name", f"Producto {p.get('id')}") for p in top_5)
            context = f"Tus productos más vendidos son: {product_names}"

            suggestion_text = await AIService.generate_suggestion(
                context=context, suggestion_type="upsell"
            )
            if suggestion_text:
                suggestions.append(
                    {
                        "type": "sales",
                        "priority": "medium",
                        "content": suggestion_text,
                        "action": "review_bundles",
                    }
                )

    except Exception as e:
        if isinstance(e, SQLAlchemyError):
            db.rollback()
        logger.warning(f"Error generating sales suggestions: {e}")

    try:
        # 3. Patrones de cobros/pagos
        payments = query_readonly(db, "cobros_pagos", {})
        if payments["cards"][0]["data"]:
            payment_data = payments["cards"][0]["data"]
            context = f"Transacciones bancarias: {len(payment_data)} registros con datos de tipo y estado"

            suggestion_text = await AIService.generate_suggestion(
                context=context, suggestion_type="cash_flow"
            )
            if suggestion_text:
                suggestions.append(
                    {
                        "type": "finance",
                        "priority": "medium",
                        "content": suggestion_text,
                        "action": "review_cash_flow",
                    }
                )

    except Exception as e:
        if isinstance(e, SQLAlchemyError):
            db.rollback()
        logger.warning(f"Error generating finance suggestions: {e}")

    return suggestions
