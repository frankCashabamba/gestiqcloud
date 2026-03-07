from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.products import Product
from app.models.expenses.expense import Expense
from app.models.production._cost_drivers import ProductionOrderCost
from app.models.production.production_order import ProductionOrder

from ...infrastructure.repositories import ExpenseRepo
from .schemas import ExpenseCreate, ExpenseOut, ExpenseUpdate

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _is_locked_production_expense(expense: Expense) -> bool:
    return bool(
        (expense.category == "production")
        or str(getattr(expense, "invoice_number", "") or "").startswith("PROD-")
    )


def _get_production_order_number(expense: Expense) -> str | None:
    invoice = str(getattr(expense, "invoice_number", "") or "")
    if not invoice.startswith("PROD-"):
        return None
    return invoice.replace("PROD-", "", 1) or None


def _find_production_order(
    db: Session, tenant_id: UUID, expense: Expense
) -> ProductionOrder | None:
    order_number = _get_production_order_number(expense)
    if not order_number:
        return None
    stmt = (
        select(ProductionOrder)
        .where(
            ProductionOrder.tenant_id == tenant_id,
            ProductionOrder.order_number == order_number,
        )
        .order_by(ProductionOrder.completed_at.desc(), ProductionOrder.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def _resolve_order_cost_total(cost: ProductionOrderCost) -> float:
    stored_total = getattr(cost, "cost_total", None)
    if stored_total is not None:
        return float(stored_total)
    qty_actual = float(cost.qty_actual or 0)
    rate_applied = float(cost.rate_applied or 0)
    headcount_actual = max(int(cost.headcount_actual or 1), 1)
    return qty_actual * rate_applied * headcount_actual


def _build_production_breakdown(db: Session, order: ProductionOrder) -> dict:
    product_ids = [line.ingredient_product_id for line in order.lines if line.ingredient_product_id]
    product_map: dict = {}
    if product_ids:
        products = db.execute(select(Product).where(Product.id.in_(product_ids))).scalars().all()
        product_map = {product.id: product for product in products}

    lines = []
    materials_total = 0.0
    for line in order.lines:
        qty_consumed = float(line.qty_consumed or line.qty_required or 0)
        stored_cost_total = getattr(line, "cost_total", None)
        cost_total = (
            float(stored_cost_total)
            if stored_cost_total is not None
            else float((line.qty_consumed or line.qty_required or 0) * (line.cost_unit or 0))
        )
        cost_unit = (cost_total / qty_consumed) if qty_consumed > 0 else float(line.cost_unit or 0)
        product = product_map.get(line.ingredient_product_id)
        lines.append(
            {
                "ingredient_name": product.name if product else "Unknown",
                "qty_consumed": qty_consumed,
                "unit": line.unit or "unit",
                "cost_unit": cost_unit,
                "cost_total": cost_total,
            }
        )
        materials_total += cost_total

    indirect_costs = []
    indirect_total = 0.0
    order_costs = (
        db.query(ProductionOrderCost)
        .filter(ProductionOrderCost.order_id == order.id)
        .order_by(ProductionOrderCost.created_at.asc())
        .all()
    )
    for cost in order_costs:
        cost_total = _resolve_order_cost_total(cost)
        indirect_costs.append(
            {
                "driver_name": cost.driver.name if cost.driver else "Indirect cost",
                "driver_unit": cost.driver.unit if cost.driver else None,
                "qty_actual": float(cost.qty_actual or 0),
                "headcount_actual": int(cost.headcount_actual or 1),
                "rate_applied": float(cost.rate_applied or 0),
                "cost_total": cost_total,
                "notes": cost.notes,
            }
        )
        indirect_total += cost_total

    grand_total = round(materials_total + indirect_total, 2)
    return {
        "lines": lines,
        "materials_total": round(materials_total, 2),
        "indirect_costs": indirect_costs,
        "indirect_total": round(indirect_total, 2),
        "grand_total": grand_total,
    }


def _sync_production_expense(db: Session, tenant_id: UUID, expense: Expense) -> bool:
    if not _is_locked_production_expense(expense):
        return False
    order = _find_production_order(db, tenant_id, expense)
    if not order:
        return False
    breakdown = _build_production_breakdown(db, order)
    grand_total = breakdown["grand_total"]
    amount = round(float(expense.amount or 0), 2)
    total = round(float(getattr(expense, "total", expense.amount or 0) or 0), 2)
    if amount == grand_total and total == grand_total:
        return False
    expense.amount = grand_total
    expense.total = grand_total
    expense.vat = 0
    return True


@router.get("", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = UUID(claims["tenant_id"])
    items = ExpenseRepo(db).list(tenant_id)
    changed = False
    for expense in items:
        changed = _sync_production_expense(db, tenant_id, expense) or changed
    if changed:
        db.commit()
    return items


@router.get("/stats")
def get_expense_stats(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    """Get expense statistics (must come before /{expense_id})"""
    from sqlalchemy import case
    from sqlalchemy import func as sqlfunc

    tenant_id = UUID(claims["tenant_id"])
    row = (
        db.query(
            sqlfunc.coalesce(sqlfunc.sum(Expense.total), 0).label("total"),
            sqlfunc.coalesce(
                sqlfunc.sum(
                    case(
                        (Expense.status == "pending", Expense.total),
                        (
                            Expense.status == "partial",
                            sqlfunc.coalesce(Expense.pending_amount, Expense.total),
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("pending"),
        )
        .filter(Expense.tenant_id == tenant_id)
        .one()
    )
    return {"total": float(row.total), "pending": float(row.pending)}


@router.get("/{expense_id}/production-detail")
def get_expense_production_detail(
    expense_id: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    """Return ingredient breakdown for a production expense."""
    tenant_id = UUID(claims["tenant_id"])
    expense = ExpenseRepo(db).get(tenant_id, expense_id)
    if not expense:
        raise HTTPException(404, "Expense not found")

    if not _is_locked_production_expense(expense):
        raise HTTPException(400, "Not a production expense")

    order_number = _get_production_order_number(expense)
    if not order_number:
        raise HTTPException(404, "No order ref in invoice_number")

    order = _find_production_order(db, tenant_id, expense)
    if not order:
        raise HTTPException(404, f"Production order '{order_number}' not found")

    breakdown = _build_production_breakdown(db, order)
    if _sync_production_expense(db, tenant_id, expense):
        db.commit()

    return {
        "expense_id": str(expense_id),
        "order_number": order_number,
        "recipe_name": (
            expense.concept.replace("Production cost - ", "").rsplit(" (", 1)[0]
            if expense.concept
            else ""
        ),
        "qty_produced": float(order.qty_produced or 0),
        "materials_total": breakdown["materials_total"],
        "indirect_costs": breakdown["indirect_costs"],
        "indirect_total": breakdown["indirect_total"],
        "total_cost": float(expense.amount or 0),
        "lines": breakdown["lines"],
    }


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = UUID(claims["tenant_id"])
    obj = ExpenseRepo(db).get(tenant_id, expense_id)
    if not obj:
        raise HTTPException(404, "Not found")
    if _sync_production_expense(db, tenant_id, obj):
        db.commit()
    return obj


@router.post("", response_model=ExpenseOut)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]
    return ExpenseRepo(db).create(tenant_id, user_id=user_id, **payload.model_dump())


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    current = ExpenseRepo(db).get(tenant_id, expense_id)
    if not current:
        raise HTTPException(404, "Not found")
    if _is_locked_production_expense(current):
        raise HTTPException(403, "Production expenses are system-generated and cannot be edited")
    try:
        return ExpenseRepo(db).update(tenant_id, expense_id, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "Not found")


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        ExpenseRepo(db).delete(tenant_id, expense_id)
    except ValueError:
        raise HTTPException(404, "Not found")
    return {"success": True}
