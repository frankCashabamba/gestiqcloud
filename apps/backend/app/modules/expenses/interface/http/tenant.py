from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
