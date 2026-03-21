from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.rls import tenant_id_sql_expr_text
from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)


def _tenant_where(alias: str | None = None) -> tuple[str, dict[str, Any]]:
    col = f"{alias}.tenant_id" if alias else "tenant_id"
    return f"{col} = {tenant_id_sql_expr_text('tid')}", {"tid": None}


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
        where_clause, tenant_params = _tenant_where("so")
        sql = (
            "SELECT date_trunc('month', so.created_at)::date AS mes, count(*) AS pedidos, "
            "coalesce(sum(so.total), 0) AS total "
            f"FROM sales_orders so WHERE {where_clause} "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 12"
        )
        rows = _fetch_all(db, sql, tenant_params)
        return {"cards": [{"title": "Pedidos por mes", "series": rows}], "sql": sql}

    if topic == "ventas_por_almacen":
        where_clause, tenant_params = _tenant_where("sm")
        sql = (
            "SELECT w.code AS almacen, sum(sm.qty) AS unidades "
            "FROM stock_moves sm JOIN warehouses w ON w.id=sm.warehouse_id "
            f"WHERE {where_clause} AND sm.kind='issue' GROUP BY 1 ORDER BY 2 DESC"
        )
        rows = _fetch_all(db, sql, tenant_params)
        return {"cards": [{"title": "Salidas por almacén", "data": rows}], "sql": sql}

    if topic == "top_productos":
        # Filter tenant via sales_orders (sales_order_items has no tenant_id column)
        where_clause, tenant_params = _tenant_where("so")
        sql = (
            "SELECT p.id, p.name, sum(soi.quantity) AS uds, "
            "sum(soi.quantity * soi.unit_price) AS importe "
            "FROM sales_order_items soi "
            "JOIN products p ON p.id = soi.product_id "
            "JOIN sales_orders so ON so.id = soi.sales_order_id "
            f"WHERE {where_clause} "
            "GROUP BY 1,2 ORDER BY importe DESC NULLS LAST LIMIT 10"
        )
        return _safe_topic(db, "Top productos", sql, lambda: _fetch_all(db, sql, tenant_params))

    if topic == "stock_bajo":
        threshold = float(p.get("threshold", 5))
        where_clause, tenant_params = _tenant_where("si")
        sql = (
            "SELECT w.code AS almacen, si.product_id, si.qty FROM stock_items si "
            f"JOIN warehouses w ON w.id=si.warehouse_id WHERE {where_clause} AND si.qty < :th ORDER BY si.qty ASC LIMIT 50"
        )
        params = {**tenant_params, "th": threshold}
        rows = _fetch_all(db, sql, params)
        return {"cards": [{"title": "Stock bajo", "data": rows}], "sql": sql}

    if topic == "pendientes_sri_sii":
        where_clause, tenant_params = _tenant_where()
        sql_sri = f"SELECT count(*) AS pendientes FROM sri_submissions WHERE {where_clause} AND status NOT IN ('AUTHORIZED')"
        sql_sii = f"SELECT count(*) AS pendientes FROM sii_batches WHERE {where_clause} AND status NOT IN ('ACCEPTED')"
        sri = _fetch_all(db, sql_sri, tenant_params.copy())
        sii = _fetch_all(db, sql_sii, tenant_params.copy())
        return {
            "cards": [
                {"title": "SRI pendientes", "data": sri},
                {"title": "SII pendientes", "data": sii},
            ],
            "sql": sql_sri + ";" + sql_sii,
        }

    if topic == "cobros_pagos":
        # Cobros = ventas confirmadas por mes, Pagos = gastos por mes
        where_s, tenant_params = _tenant_where("so")
        where_e, _ = _tenant_where("e")
        sql = (
            "SELECT mes, sum(cobros) AS cobros, sum(pagos) AS pagos FROM ("
            f"  SELECT date_trunc('month', so.created_at)::date AS mes, "
            f"  coalesce(sum(so.total), 0) AS cobros, 0::numeric AS pagos "
            f"  FROM sales_orders so WHERE {where_s} "
            f"  AND so.status NOT IN ('draft', 'voided', 'cancelled') "
            "  GROUP BY 1 "
            "  UNION ALL "
            f"  SELECT date_trunc('month', e.date)::date AS mes, "
            f"  0::numeric AS cobros, coalesce(sum(e.amount), 0) AS pagos "
            f"  FROM expenses e WHERE {where_e} "
            "  GROUP BY 1 "
            ") t GROUP BY mes ORDER BY mes DESC LIMIT 6"
        )
        return _safe_topic(db, "Cobros/Pagos", sql, lambda: _fetch_all(db, sql, tenant_params))

    if topic == "pos_hoy":
        where_clause, tenant_params = _tenant_where("r")
        sql = (
            "SELECT count(*) AS recibos, coalesce(sum(r.gross_total),0) AS total "
            f"FROM pos_receipts r WHERE {where_clause} AND r.created_at::date = CURRENT_DATE AND r.status = 'paid'"
        )
        return _safe_topic(db, "POS hoy", sql, lambda: _fetch_all(db, sql, tenant_params))

    if topic == "gastos_mes":
        where_clause, tenant_params = _tenant_where()
        sql = (
            "SELECT date_trunc('month', date)::date AS mes, count(*) AS n, "
            f"coalesce(sum(amount),0) AS total FROM expenses WHERE {where_clause} "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
        )
        return _safe_topic(db, "Gastos por mes", sql, lambda: _fetch_all(db, sql, tenant_params))

    if topic == "produccion_activa":
        where_clause, tenant_params = _tenant_where()
        sql = (
            f"SELECT status, count(*) AS n FROM production_orders WHERE {where_clause} "
            "AND status IN ('planned','in_progress') GROUP BY 1"
        )
        return _safe_topic(db, "Producción activa", sql, lambda: _fetch_all(db, sql, tenant_params))

    if topic == "compras_pendientes":
        where_clause, tenant_params = _tenant_where()
        sql = (
            "SELECT count(*) AS total, coalesce(sum(total_amount),0) AS monto "
            f"FROM purchase_orders WHERE {where_clause} AND status IN ('draft','sent','confirmed')"
        )
        return _safe_topic(
            db, "Compras pendientes", sql, lambda: _fetch_all(db, sql, tenant_params)
        )

    if topic == "prediccion_reorden":
        where_clause, tenant_params = _tenant_where("sm")
        sql = (
            "SELECT p.name, p.id AS product_id, "
            "coalesce(sum(sm.qty) / NULLIF(count(DISTINCT sm.occurred_at::date), 0), 0) AS consumo_diario, "
            "coalesce(si.qty, 0) AS stock_actual "
            "FROM stock_moves sm "
            "JOIN products p ON p.id = sm.product_id "
            "LEFT JOIN stock_items si ON si.product_id = sm.product_id "
            f"WHERE {where_clause} AND sm.kind = 'sale' "
            "AND sm.occurred_at > CURRENT_DATE - INTERVAL '30 days' "
            "GROUP BY p.name, p.id, si.qty "
            "HAVING coalesce(si.qty, 0) > 0 "
            "ORDER BY coalesce(si.qty, 0) / NULLIF(coalesce(sum(sm.qty) / NULLIF(count(DISTINCT sm.occurred_at::date), 0), 0), 0) ASC "
            "LIMIT 10"
        )
        return _safe_topic(
            db, "Predicción reorden", sql, lambda: _fetch_all(db, sql, tenant_params)
        )

    if topic == "anomalias_ventas":
        # Detecta días con ventas POS < 60% del promedio de los últimos 30 días
        where_clause, tenant_params = _tenant_where("pr")
        sql = (
            "WITH daily AS ("
            "  SELECT created_at::date AS dia, coalesce(sum(gross_total), 0) AS total_dia "
            "  FROM pos_receipts pr "
            f" WHERE {where_clause} AND pr.status = 'paid' "
            "  AND pr.created_at > CURRENT_DATE - INTERVAL '30 days' "
            "  GROUP BY 1"
            "), promedio AS ("
            "  SELECT avg(total_dia) AS avg_30d FROM daily"
            ") "
            "SELECT d.dia, d.total_dia, p.avg_30d, "
            "  round((d.total_dia / NULLIF(p.avg_30d, 0) * 100)::numeric, 1) AS pct_vs_promedio "
            "FROM daily d, promedio p "
            "WHERE d.total_dia < p.avg_30d * 0.6 "
            "ORDER BY d.dia DESC LIMIT 10"
        )
        return _safe_topic(
            db,
            "Días con ventas anómalas (< 60% del promedio)",
            sql,
            lambda: _fetch_all(db, sql, tenant_params),
        )

    if topic == "clasificar_gasto":
        description = str(p.get("description", ""))
        amount = float(p.get("amount", 0))
        if not description:
            return {"cards": [], "note": "description_required"}
        # Return data for AI classification
        where_clause, tenant_params = _tenant_where()
        sql = (
            f"SELECT DISTINCT category FROM expenses WHERE {where_clause} "
            "AND category IS NOT NULL ORDER BY category"
        )
        categories = _fetch_all(db, sql, tenant_params)
        cat_list = [r.get("category", "") for r in categories if r.get("category")]
        return {
            "cards": [
                {
                    "title": "Clasificación de gasto",
                    "data": {
                        "description": description,
                        "amount": amount,
                        "existing_categories": cat_list,
                    },
                }
            ],
            "sql": sql,
            "ai_classification_needed": True,
        }

    # Default: unsupported
    return {"cards": [], "sql": None, "note": "topic_unsupported"}


def create_invoice_draft(
    db: Session, tenant_empresa_id: str, payload: dict[str, Any]
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
            "emp": tenant_empresa_id,
            "cli": cliente_id,
            "sub": subtotal,
            "iva": iva,
            "tot": total,
        },
    ).first()
    assert row is not None
    return {"id": str(row[0]), "status": "draft"}


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
    return {"id": str(oid), "status": "draft"}


def create_transfer_draft(
    db: Session, payload: dict[str, Any], tenant_id: str | None = None
) -> dict[str, Any]:
    # Draft transfer: two stock_move tentative rows (no stock_items update)
    src = str(payload.get("from_warehouse_id") or "")
    dst = str(payload.get("to_warehouse_id") or "")
    prod = str(payload.get("product_id") or "")
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
    card0 = result.get("cards", [{}])[0] if result.get("cards") else {}
    if not result.get("cards") or (not card0.get("data") and not card0.get("series")):
        return result

    # 3. Mejorar con IA si se solicita
    if with_ai_insights:
        try:
            # UUID/Decimal/datetime can appear in DB rows; stringify non-JSON-native values.
            summary = json.dumps(result["cards"], indent=2, ensure_ascii=False, default=str)
            topic_display = topic.replace("_", " ").title()

            # Limit data sent to AI to avoid long prompts
            cards_data = (result["cards"][0].get("data") or result["cards"][0].get("series") or [])[:10]
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
            context = (
                f"Transacciones bancarias: {len(payment_data)} registros con datos de tipo y estado"
            )

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
