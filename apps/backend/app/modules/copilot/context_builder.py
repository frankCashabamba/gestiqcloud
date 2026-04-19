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

from app.modules.accounting.application.context import get_context_summary as get_accounting_context
from app.modules.clients.application.context import get_context_summary as get_clients_context
from app.modules.copilot.catalog import CONTEXT_LOADERS, resolve_context_module
from app.modules.copilot.services import pii_mask_row
from app.modules.crm.application.context import get_context_summary as get_crm_context
from app.modules.einvoicing.application.context import get_context_summary as get_einvoicing_context
from app.modules.expenses.application.context import get_context_summary as get_expenses_context
from app.modules.finance.application.context import get_context_summary as get_finance_context
from app.modules.hr.application.context import get_context_summary as get_hr_context
from app.modules.inventory.application.context import get_context_summary as get_inventory_context
from app.modules.invoicing.application.context import get_context_summary as get_invoicing_context
from app.modules.notifications.application.context import (
    get_context_summary as get_notifications_context,
)
from app.modules.pos.application.context import get_context_summary as get_pos_context
from app.modules.production.context import get_context_summary as get_production_context
from app.modules.products.application.context import get_context_summary as get_products_context
from app.modules.purchases.infrastructure.context import (
    get_context_summary as get_purchases_context,
)
from app.modules.reconciliation.application.context import (
    get_context_summary as get_reconciliation_context,
)
from app.modules.reports.application.context import get_context_summary as get_reports_context
from app.modules.sales.application.context import get_context_summary as get_sales_context
from app.modules.settings.application.context import get_context_summary as get_settings_context
from app.modules.suppliers.infrastructure.context import (
    get_context_summary as get_suppliers_context,
)
from app.modules.users.application.context import get_context_summary as get_users_context

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
        return get_pos_context(db, tid)

    @staticmethod
    def _inventory(db: Session, tid: str) -> dict[str, Any]:
        return get_inventory_context(db, tid)

    @staticmethod
    def _purchases(db: Session, tid: str) -> dict[str, Any]:
        return get_purchases_context(db, tid)

    @staticmethod
    def _sales(db: Session, tid: str) -> dict[str, Any]:
        return get_sales_context(db, tid)

    @staticmethod
    def _finance(db: Session, tid: str) -> dict[str, Any]:
        return get_finance_context(db, tid)

    @staticmethod
    def _manufacturing(db: Session, tid: str) -> dict[str, Any]:
        return get_production_context(db, tid)

    @staticmethod
    def _expenses(db: Session, tid: str) -> dict[str, Any]:
        return get_expenses_context(db, tid)

    @staticmethod
    def _hr(db: Session, tid: str) -> dict[str, Any]:
        return get_hr_context(db, tid)

    @staticmethod
    def _products(db: Session, tid: str) -> dict[str, Any]:
        return get_products_context(db, tid)

    @staticmethod
    def _crm(db: Session, tid: str) -> dict[str, Any]:
        return get_crm_context(db, tid)

    @staticmethod
    def _customers(db: Session, tid: str) -> dict[str, Any]:
        return get_clients_context(db, tid)

    @staticmethod
    def _suppliers(db: Session, tid: str) -> dict[str, Any]:
        return get_suppliers_context(db, tid)

    @staticmethod
    def _accounting(db: Session, tid: str) -> dict[str, Any]:
        return get_accounting_context(db, tid)

    @staticmethod
    def _invoicing(db: Session, tid: str) -> dict[str, Any]:
        return get_invoicing_context(db, tid)

    @staticmethod
    def _einvoicing(db: Session, tid: str) -> dict[str, Any]:
        return get_einvoicing_context(db, tid)

    @staticmethod
    def _reconciliation(db: Session, tid: str) -> dict[str, Any]:
        return get_reconciliation_context(db, tid)

    @staticmethod
    def _reports(db: Session, tid: str) -> dict[str, Any]:
        return get_reports_context(db, tid)

    @staticmethod
    def _notifications(db: Session, tid: str) -> dict[str, Any]:
        return get_notifications_context(db, tid)

    @staticmethod
    def _settings(db: Session, tid: str) -> dict[str, Any]:
        return get_settings_context(db, tid)

    @staticmethod
    def _users(db: Session, tid: str) -> dict[str, Any]:
        return get_users_context(db, tid)

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
            text("SELECT count(*) FROM stock_items WHERE tenant_id = :tid AND qty < 5"),
            {"tid": tid},
        ).scalar()

        return {
            "modulo": "General",
            "total_productos": int(products or 0),
            "productos_stock_bajo": int(low_stock or 0),
        }
