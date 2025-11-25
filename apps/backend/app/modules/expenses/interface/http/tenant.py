from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

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


@router.get("", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    return ExpenseRepo(db).list(tenant_id)


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
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
    return ExpenseRepo(db).create(tenant_id, **payload.model_dump())


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    try:
        return ExpenseRepo(db).update(tenant_id, expense_id, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "Not found")


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        ExpenseRepo(db).delete(tenant_id, expense_id)
    except ValueError:
        raise HTTPException(404, "Not found")
    return {"success": True}
