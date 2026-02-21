from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.expenses.expense import Expense

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


@router.get("", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    return ExpenseRepo(db).list(tenant_id)


@router.get("/stats")
def get_expense_stats(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    """Get expense statistics (must come before /{expense_id})"""
    return {"total": 0, "pending": 0}


@router.get("/{expense_id}/production-detail")
def get_expense_production_detail(
    expense_id: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    """Return ingredient breakdown for a production expense."""
    tenant_id = UUID(claims["tenant_id"])
    expense = ExpenseRepo(db).get(tenant_id, expense_id)
    print(f"[PROD-DETAIL] expense_id={expense_id}, found={expense is not None}")
    if not expense:
        raise HTTPException(404, "Expense not found")

    is_prod = _is_locked_production_expense(expense)
    print(f"[PROD-DETAIL] category='{expense.category}' invoice='{expense.invoice_number}' is_prod={is_prod}")
    if not is_prod:
        raise HTTPException(400, "Not a production expense")

    invoice = getattr(expense, "invoice_number", "") or ""
    order_number = invoice.replace("PROD-", "", 1) if invoice.startswith("PROD-") else None
    print(f"[PROD-DETAIL] order_number='{order_number}'")
    if not order_number:
        raise HTTPException(404, f"No order ref in invoice_number='{invoice}'")

    from app.models.production.production_order import ProductionOrder
    from app.models.core.products import Product

    order = db.execute(
        select(ProductionOrder).where(
            ProductionOrder.tenant_id == tenant_id,
            ProductionOrder.order_number == order_number,
        )
    ).scalar_one_or_none()
    if not order:
        # Debug: try without tenant filter
        any_order = db.execute(
            select(ProductionOrder).where(ProductionOrder.order_number == order_number)
        ).scalar_one_or_none()
        print(f"[PROD-DETAIL] order NOT found. Without tenant filter: {any_order is not None}")
        if any_order:
            print(f"[PROD-DETAIL] tenant mismatch: order={any_order.tenant_id} vs claim={tenant_id}")
        raise HTTPException(404, f"Production order '{order_number}' not found")

    lines = []
    for line in order.lines:
        product = db.execute(
            select(Product).where(Product.id == line.ingredient_product_id)
        ).scalar_one_or_none()
        lines.append({
            "ingredient_name": product.name if product else "Unknown",
            "qty_consumed": float(line.qty_consumed or line.qty_required or 0),
            "unit": line.unit or "unit",
            "cost_unit": float(line.cost_unit or 0),
            "cost_total": float((line.qty_consumed or line.qty_required or 0) * (line.cost_unit or 0)),
        })

    return {
        "expense_id": str(expense_id),
        "order_number": order_number,
        "recipe_name": expense.concept.replace("Production cost - ", "").rsplit(" (", 1)[0] if expense.concept else "",
        "qty_produced": float(order.qty_produced or 0),
        "total_cost": float(expense.amount or 0),
        "lines": lines,
    }


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    obj = ExpenseRepo(db).get(tenant_id, expense_id)
    if not obj:
        raise HTTPException(404, "Not found")
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
