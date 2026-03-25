"""
CopilotContextBuilder — Construye contexto específico por módulo para el chat IA.

Cada módulo tiene un loader que consulta datos relevantes del tenant
y los entrega como contexto estructurado al prompt del copilot.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.copilot.catalog import CONTEXT_LOADERS, resolve_context_module
from app.modules.copilot.services import pii_mask_row

logger = logging.getLogger(__name__)


class CopilotContextBuilder:
    LOADERS: dict[str, str] = dict(CONTEXT_LOADERS)

    @classmethod
    def build(cls, db: Session, tenant_id: str, module: str | None) -> str:
        method_name = cls.LOADERS.get(resolve_context_module(module) or "", "_general")
        loader = getattr(cls, method_name, cls._general)
        try:
            raw = loader(db, tenant_id)
        except Exception as e:
            logger.warning("Context loader %s failed: %s", method_name, e)
            try:
                db.rollback()
            except Exception:
                pass
            raw = {"error": f"context_unavailable:{type(e).__name__}"}
        if isinstance(raw, list):
            raw = [pii_mask_row(r) if isinstance(r, dict) else r for r in raw]
        elif isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, list):
                    raw[k] = [pii_mask_row(r) if isinstance(r, dict) else r for r in v]
        return json.dumps(raw, default=str, ensure_ascii=False)

    @staticmethod
    def _pos(db: Session, tid: str) -> dict[str, Any]:
        shift = db.execute(
            text(
                "SELECT id, status, opened_at, opening_float FROM pos_shifts "
                "WHERE tenant_id = :tid AND status = 'open' ORDER BY opened_at DESC LIMIT 1"
            ),
            {"tid": tid},
        ).fetchone()

        sales = db.execute(
            text(
                "SELECT count(*) AS recibos, coalesce(sum(gross_total),0) AS total "
                "FROM pos_receipts WHERE tenant_id = :tid AND created_at::date = CURRENT_DATE"
            ),
            {"tid": tid},
        ).fetchone()

        top = db.execute(
            text(
                "SELECT p.name, sum(rl.qty) AS qty, sum(rl.line_total) AS total "
                "FROM pos_receipt_lines rl JOIN products p ON p.id = rl.product_id "
                "JOIN pos_receipts r ON r.id = rl.receipt_id "
                "WHERE r.tenant_id = :tid AND r.created_at::date = CURRENT_DATE "
                "GROUP BY p.name ORDER BY total DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "POS",
            "turno_activo": dict(shift._mapping) if shift else None,
            "ventas_hoy": dict(sales._mapping) if sales else {},
            "top_productos_hoy": [dict(r._mapping) for r in top],
        }

    @staticmethod
    def _inventory(db: Session, tid: str) -> dict[str, Any]:
        low_stock = db.execute(
            text(
                "SELECT p.name, si.qty, w.code AS almacen "
                "FROM stock_items si "
                "JOIN products p ON p.id = si.product_id "
                "JOIN warehouses w ON w.id = si.warehouse_id "
                "WHERE si.tenant_id = :tid AND si.qty < 5 "
                "ORDER BY si.qty ASC LIMIT 10"
            ),
            {"tid": tid},
        ).fetchall()

        total_value = db.execute(
            text(
                "SELECT coalesce(sum(on_hand_qty * avg_cost), 0) AS valor "
                "FROM inventory_cost_state WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()

        no_movement = db.execute(
            text(
                "SELECT p.name, si.qty "
                "FROM stock_items si "
                "JOIN products p ON p.id = si.product_id "
                "WHERE si.tenant_id = :tid AND si.qty > 0 "
                "AND si.product_id NOT IN ("
                "  SELECT DISTINCT product_id FROM stock_moves "
                "  WHERE tenant_id = :tid AND occurred_at > CURRENT_DATE - INTERVAL '30 days'"
                ") LIMIT 10"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "Inventario",
            "stock_bajo": [dict(r._mapping) for r in low_stock],
            "valor_total_inventario": float(total_value[0]) if total_value else 0,
            "sin_movimiento_30d": [dict(r._mapping) for r in no_movement],
        }

    @staticmethod
    def _purchases(db: Session, tid: str) -> dict[str, Any]:
        pending = db.execute(
            text(
                "SELECT count(*) AS total, coalesce(sum(total_amount), 0) AS monto "
                "FROM purchase_orders WHERE tenant_id = :tid AND status IN ('draft', 'sent', 'confirmed')"
            ),
            {"tid": tid},
        ).fetchone()

        recent = db.execute(
            text(
                "SELECT po.id, s.name AS proveedor, po.total_amount, po.status, po.created_at "
                "FROM purchase_orders po "
                "LEFT JOIN suppliers s ON s.id = po.supplier_id "
                "WHERE po.tenant_id = :tid "
                "ORDER BY po.created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "Compras",
            "ordenes_pendientes": dict(pending._mapping) if pending else {},
            "ultimas_ordenes": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _sales(db: Session, tid: str) -> dict[str, Any]:
        monthly = db.execute(
            text(
                "SELECT date_trunc('month', created_at)::date AS mes, "
                "count(*) AS pedidos, coalesce(sum(total_amount), 0) AS total "
                "FROM sales_orders WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
            ),
            {"tid": tid},
        ).fetchall()

        top_clients = db.execute(
            text(
                "SELECT c.name, count(*) AS pedidos, coalesce(sum(so.total_amount), 0) AS total "
                "FROM sales_orders so "
                "JOIN clients c ON c.id = so.customer_id "
                "WHERE so.tenant_id = :tid "
                "GROUP BY c.name ORDER BY total DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "Ventas",
            "ventas_por_mes": [dict(r._mapping) for r in monthly],
            "top_clientes": [dict(r._mapping) for r in top_clients],
        }

    @staticmethod
    def _finance(db: Session, tid: str) -> dict[str, Any]:
        bank_summary = db.execute(
            text(
                "SELECT type::text AS tipo, count(*) AS n, coalesce(sum(amount), 0) AS total "
                "FROM bank_transactions WHERE tenant_id = :tid "
                "GROUP BY type ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "Finanzas",
            "resumen_bancario": [dict(r._mapping) for r in bank_summary],
        }

    @staticmethod
    def _manufacturing(db: Session, tid: str) -> dict[str, Any]:
        active = db.execute(
            text(
                "SELECT count(*) AS total FROM production_orders "
                "WHERE tenant_id = :tid AND status IN ('in_progress', 'planned')"
            ),
            {"tid": tid},
        ).fetchone()

        return {
            "modulo": "Producción",
            "ordenes_activas": int(active[0]) if active else 0,
        }

    @staticmethod
    def _expenses(db: Session, tid: str) -> dict[str, Any]:
        monthly = db.execute(
            text(
                "SELECT date_trunc('month', date)::date AS mes, "
                "count(*) AS n, coalesce(sum(amount), 0) AS total "
                "FROM expenses WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
            ),
            {"tid": tid},
        ).fetchall()

        return {
            "modulo": "Gastos",
            "gastos_por_mes": [dict(r._mapping) for r in monthly],
        }

    @staticmethod
    def _hr(db: Session, tid: str) -> dict[str, Any]:
        employees = db.execute(
            text(
                "SELECT count(*) AS total FROM employees "
                "WHERE tenant_id = :tid AND is_active = true"
            ),
            {"tid": tid},
        ).fetchone()

        return {
            "modulo": "RRHH",
            "empleados_activos": int(employees[0]) if employees else 0,
        }

    @staticmethod
    def _products(db: Session, tid: str) -> dict[str, Any]:
        stats = db.execute(
            text(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE active = true) AS activos "
                "FROM products WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()

        return {
            "modulo": "Productos",
            "total_productos": int(stats[0]) if stats else 0,
            "productos_activos": int(stats[1]) if stats else 0,
        }

    @staticmethod
    def _crm(db: Session, tid: str) -> dict[str, Any]:
        leads = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total "
                "FROM crm_leads WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()
        opportunities = db.execute(
            text(
                "SELECT stage::text AS etapa, count(*) AS total, coalesce(sum(value), 0) AS valor "
                "FROM crm_opportunities WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY valor DESC"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "CRM",
            "leads_por_estado": [dict(r._mapping) for r in leads],
            "oportunidades_por_etapa": [dict(r._mapping) for r in opportunities],
        }

    @staticmethod
    def _customers(db: Session, tid: str) -> dict[str, Any]:
        stats = db.execute(
            text(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE is_wholesale = true) AS mayoristas "
                "FROM clients WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()
        recent = db.execute(
            text(
                "SELECT name, city, email, phone "
                "FROM clients WHERE tenant_id = :tid "
                "ORDER BY id DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Clientes",
            "total_clientes": int(stats[0]) if stats else 0,
            "clientes_mayoristas": int(stats[1]) if stats else 0,
            "ultimos_clientes": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _suppliers(db: Session, tid: str) -> dict[str, Any]:
        stats = db.execute(
            text(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE is_active = true) AS activos "
                "FROM suppliers WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()
        recent = db.execute(
            text(
                "SELECT name, email, phone, created_at "
                "FROM suppliers WHERE tenant_id = :tid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Proveedores",
            "total_proveedores": int(stats[0]) if stats else 0,
            "proveedores_activos": int(stats[1]) if stats else 0,
            "ultimos_proveedores": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _accounting(db: Session, tid: str) -> dict[str, Any]:
        statuses = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total, "
                "coalesce(sum(debit_total), 0) AS debito "
                "FROM journal_entries WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()
        recent = db.execute(
            text(
                "SELECT number, date, status::text AS status, debit_total, credit_total "
                "FROM journal_entries WHERE tenant_id = :tid "
                "ORDER BY date DESC, created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Contabilidad",
            "asientos_por_estado": [dict(r._mapping) for r in statuses],
            "ultimos_asientos": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _invoicing(db: Session, tid: str) -> dict[str, Any]:
        statuses = db.execute(
            text(
                "SELECT status AS estado, count(*) AS total, coalesce(sum(total), 0) AS monto "
                "FROM invoices WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY monto DESC"
            ),
            {"tid": tid},
        ).fetchall()
        recent = db.execute(
            text(
                "SELECT number, supplier, total, status, created_at "
                "FROM invoices WHERE tenant_id = :tid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Facturación",
            "facturas_por_estado": [dict(r._mapping) for r in statuses],
            "ultimas_facturas": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _einvoicing(db: Session, tid: str) -> dict[str, Any]:
        sri = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total "
                "FROM sri_submissions WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()
        sii = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total "
                "FROM sii_batches WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Facturación Electrónica",
            "sri_por_estado": [dict(r._mapping) for r in sri],
            "sii_por_estado": [dict(r._mapping) for r in sii],
        }

    @staticmethod
    def _reconciliation(db: Session, tid: str) -> dict[str, Any]:
        transactions = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total, coalesce(sum(amount), 0) AS monto "
                "FROM bank_transactions WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY monto DESC"
            ),
            {"tid": tid},
        ).fetchall()
        reconciliations = db.execute(
            text(
                "SELECT status::text AS estado, count(*) AS total, coalesce(sum(difference), 0) AS diferencia "
                "FROM bank_reconciliations WHERE tenant_id = :tid "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Conciliación",
            "transacciones_bancarias": [dict(r._mapping) for r in transactions],
            "conciliaciones_por_estado": [dict(r._mapping) for r in reconciliations],
        }

    @staticmethod
    def _reports(db: Session, tid: str) -> dict[str, Any]:
        sales = db.execute(
            text(
                "SELECT coalesce(sum(total_amount), 0) AS ventas "
                "FROM sales_orders WHERE tenant_id = :tid "
                "AND created_at > CURRENT_DATE - INTERVAL '30 days'"
            ),
            {"tid": tid},
        ).fetchone()
        expenses = db.execute(
            text(
                "SELECT coalesce(sum(amount), 0) AS gastos "
                "FROM expenses WHERE tenant_id = :tid "
                "AND date > CURRENT_DATE - INTERVAL '30 days'"
            ),
            {"tid": tid},
        ).fetchone()
        invoices = db.execute(
            text(
                "SELECT count(*) AS total, coalesce(sum(total), 0) AS facturado "
                "FROM invoices WHERE tenant_id = :tid "
                "AND created_at::timestamp > CURRENT_DATE - INTERVAL '30 days'"
            ),
            {"tid": tid},
        ).fetchone()
        return {
            "modulo": "Reportes",
            "ventas_30d": float(sales[0]) if sales else 0,
            "gastos_30d": float(expenses[0]) if expenses else 0,
            "facturas_30d": {
                "total": int(invoices[0]) if invoices else 0,
                "facturado": float(invoices[1]) if invoices else 0,
            },
        }

    @staticmethod
    def _notifications(db: Session, tid: str) -> dict[str, Any]:
        unread = db.execute(
            text(
                "SELECT count(*) AS total FROM notifications "
                "WHERE tenant_id = :tid AND read_at IS NULL AND archived_at IS NULL"
            ),
            {"tid": tid},
        ).fetchone()
        recent = db.execute(
            text(
                "SELECT channel, subject, priority, status, created_at "
                "FROM notifications WHERE tenant_id = :tid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        return {
            "modulo": "Notificaciones",
            "notificaciones_no_leidas": int(unread[0]) if unread else 0,
            "ultimas_notificaciones": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _settings(db: Session, tid: str) -> dict[str, Any]:
        tenant = db.execute(
            text(
                "SELECT name, sector, country, currency "
                "FROM tenants WHERE id = :tid"
            ),
            {"tid": tid},
        ).fetchone()
        return {
            "modulo": "Configuración",
            "tenant": dict(tenant._mapping) if tenant else None,
        }

    @staticmethod
    def _users(db: Session, tid: str) -> dict[str, Any]:
        stats = db.execute(
            text(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE is_active = true) AS activos, "
                "count(*) FILTER (WHERE is_company_admin = true) AS admins "
                "FROM company_users WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()
        recent = db.execute(
            text(
                "SELECT first_name, last_name, email, is_active, is_company_admin, created_at "
                "FROM company_users WHERE tenant_id = :tid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"tid": tid},
        ).fetchall()
        roles = db.execute(
            text(
                "SELECT count(*) AS total FROM company_roles WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).fetchone()
        return {
            "modulo": "Usuarios",
            "usuarios": {
                "total": int(stats[0]) if stats else 0,
                "activos": int(stats[1]) if stats else 0,
                "admins": int(stats[2]) if stats else 0,
            },
            "roles": int(roles[0]) if roles else 0,
            "ultimos_usuarios": [dict(r._mapping) for r in recent],
        }

    @staticmethod
    def _finances(db: Session, tid: str) -> dict[str, Any]:
        return CopilotContextBuilder._finance(db, tid)

    @staticmethod
    def _productions(db: Session, tid: str) -> dict[str, Any]:
        return CopilotContextBuilder._manufacturing(db, tid)

    @staticmethod
    def _general(db: Session, tid: str) -> dict[str, Any]:
        products = db.execute(
            text("SELECT count(*) FROM products WHERE tenant_id = :tid"),
            {"tid": tid},
        ).scalar()

        low_stock = db.execute(
            text("SELECT count(*) FROM stock_items " "WHERE tenant_id = :tid AND qty < 5"),
            {"tid": tid},
        ).scalar()

        return {
            "modulo": "General",
            "total_productos": int(products or 0),
            "productos_stock_bajo": int(low_stock or 0),
        }
