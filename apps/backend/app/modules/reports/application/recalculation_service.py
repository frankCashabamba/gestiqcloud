"""Recalculation Engine — Profit snapshots"""
import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.core.profit_snapshots import ProductProfitSnapshot, ProfitSnapshotDaily
from app.models.recipes import Recipe
from app.models.sales.order import SalesOrder, SalesOrderItem

logger = logging.getLogger(__name__)


class RecalculationService:
    """Recalculates profit snapshots from domain data."""

    def __init__(self, db: Session):
        self.db = db

    def recalculate_daily(
        self, tenant_id: UUID, target_date: date, location_id: UUID | None = None,
    ) -> ProfitSnapshotDaily:
        """Recalculate profit snapshot for a given day."""
        # 1. Calculate total sales for the day
        sales_query = (
            self.db.query(
                func.count(SalesOrder.id).label("order_count"),
                func.coalesce(func.sum(SalesOrder.total), 0).label("total_sales"),
            )
            .filter(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.order_date == target_date,
            )
        )
        sales_result = sales_query.first()
        order_count = sales_result[0] or 0
        total_sales = Decimal(str(sales_result[1] or 0))

        # 2. Calculate COGS from order items
        items_query = (
            self.db.query(
                func.count(SalesOrderItem.id).label("item_count"),
                func.coalesce(func.sum(SalesOrderItem.qty), 0).label("total_qty"),
            )
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
            .filter(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.order_date == target_date,
            )
        )
        items_result = items_query.first()
        item_count = items_result[0] or 0

        # Calculate COGS per product
        total_cogs = Decimal("0")
        product_snapshots = []

        # Get all order items for the day with product info
        detail_query = (
            self.db.query(
                SalesOrderItem.product_id,
                func.sum(SalesOrderItem.qty).label("sold_qty"),
                func.sum(SalesOrderItem.line_total).label("revenue"),
            )
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
            .filter(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.order_date == target_date,
            )
            .group_by(SalesOrderItem.product_id)
        )

        for row in detail_query.all():
            product_id = row[0]
            sold_qty = Decimal(str(row[1] or 0))
            revenue = Decimal(str(row[2] or 0))

            # Get unit cost from recipe or product.cost_price
            unit_cost = self._get_unit_cost(tenant_id, product_id, target_date)
            cogs = sold_qty * unit_cost
            total_cogs += cogs
            gross = revenue - cogs
            margin = (gross / revenue * 100) if revenue > 0 else Decimal("0")

            product_snapshots.append({
                "product_id": product_id,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross,
                "margin_pct": margin,
                "sold_qty": sold_qty,
            })

        # 3. Calculate expenses for the day
        total_expenses = Decimal("0")
        try:
            from app.models.expenses.expense import Expense
            exp_result = (
                self.db.query(func.coalesce(func.sum(Expense.amount), 0))
                .filter(
                    Expense.tenant_id == tenant_id,
                    Expense.date == target_date,
                )
                .scalar()
            )
            total_expenses = Decimal(str(exp_result or 0))
        except Exception:
            logger.debug("Expenses table not available or query failed")

        gross_profit = total_sales - total_cogs
        net_profit = gross_profit - total_expenses

        # 4. Upsert daily snapshot
        snapshot = (
            self.db.query(ProfitSnapshotDaily)
            .filter(
                ProfitSnapshotDaily.tenant_id == tenant_id,
                ProfitSnapshotDaily.date == target_date,
            )
            .first()
        )
        if snapshot:
            snapshot.total_sales = total_sales
            snapshot.total_cogs = total_cogs
            snapshot.gross_profit = gross_profit
            snapshot.total_expenses = total_expenses
            snapshot.net_profit = net_profit
            snapshot.order_count = order_count
            snapshot.item_count = item_count
        else:
            snapshot = ProfitSnapshotDaily(
                tenant_id=tenant_id,
                date=target_date,
                location_id=location_id,
                total_sales=total_sales,
                total_cogs=total_cogs,
                gross_profit=gross_profit,
                total_expenses=total_expenses,
                net_profit=net_profit,
                order_count=order_count,
                item_count=item_count,
            )
            self.db.add(snapshot)

        # 5. Upsert product snapshots
        for ps_data in product_snapshots:
            ps = (
                self.db.query(ProductProfitSnapshot)
                .filter(
                    ProductProfitSnapshot.tenant_id == tenant_id,
                    ProductProfitSnapshot.date == target_date,
                    ProductProfitSnapshot.product_id == ps_data["product_id"],
                )
                .first()
            )
            if ps:
                ps.revenue = ps_data["revenue"]
                ps.cogs = ps_data["cogs"]
                ps.gross_profit = ps_data["gross_profit"]
                ps.margin_pct = ps_data["margin_pct"]
                ps.sold_qty = ps_data["sold_qty"]
            else:
                ps = ProductProfitSnapshot(
                    tenant_id=tenant_id,
                    date=target_date,
                    product_id=ps_data["product_id"],
                    location_id=location_id,
                    revenue=ps_data["revenue"],
                    cogs=ps_data["cogs"],
                    gross_profit=ps_data["gross_profit"],
                    margin_pct=ps_data["margin_pct"],
                    sold_qty=ps_data["sold_qty"],
                )
                self.db.add(ps)

        self.db.flush()
        return snapshot

    def recalculate_range(
        self, tenant_id: UUID, date_from: date, date_to: date,
        location_id: UUID | None = None,
    ) -> list[ProfitSnapshotDaily]:
        """Recalculate snapshots for a date range."""
        from datetime import timedelta
        results = []
        current = date_from
        while current <= date_to:
            snap = self.recalculate_daily(tenant_id, current, location_id)
            results.append(snap)
            current += timedelta(days=1)
        self.db.flush()
        return results

    def _get_unit_cost(self, tenant_id: UUID, product_id: UUID, target_date: date) -> Decimal:
        """Get unit cost from recipe (active, versioned) or product.cost_price."""
        # Try recipe first
        recipe = (
            self.db.query(Recipe)
            .filter(
                Recipe.tenant_id == tenant_id,
                Recipe.product_id == product_id,
                Recipe.is_active == True,
            )
            .first()
        )
        if recipe and recipe.unit_cost:
            return Decimal(str(recipe.unit_cost))

        # Fallback to product.cost_price
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product and product.cost_price:
            return Decimal(str(product.cost_price))

        return Decimal("0")
