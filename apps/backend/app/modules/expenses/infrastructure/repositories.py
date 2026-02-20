from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.crud_base import CRUDBase
from app.models.expenses import Expense


@dataclass
class ExpenseCreateDTO:
    date: str | None = None
    supplier_id: UUID | None = None
    amount: float | None = None
    concept: str | None = None
    category: str | None = None
    subcategory: str | None = None
    payment_method: str | None = None
    invoice_number: str | None = None
    status: str | None = None
    notes: str | None = None
    vat: float | None = None
    total: float | None = None
    user_id: UUID | None = None

    def model_dump(self) -> dict:
        return {
            "date": self.date,
            "supplier_id": self.supplier_id,
            "amount": self.amount,
            "concept": self.concept,
            "category": self.category,
            "subcategory": self.subcategory,
            "payment_method": self.payment_method,
            "invoice_number": self.invoice_number,
            "status": self.status,
            "notes": self.notes,
            "vat": self.vat,
            "total": self.total,
            "user_id": self.user_id,
        }


@dataclass
class ExpenseUpdateDTO:
    date: str | None = None
    supplier_id: UUID | None = None
    amount: float | None = None
    concept: str | None = None
    category: str | None = None
    subcategory: str | None = None
    payment_method: str | None = None
    invoice_number: str | None = None
    status: str | None = None
    notes: str | None = None
    vat: float | None = None
    total: float | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "date": self.date,
            "supplier_id": self.supplier_id,
            "amount": self.amount,
            "concept": self.concept,
            "category": self.category,
            "subcategory": self.subcategory,
            "payment_method": self.payment_method,
            "invoice_number": self.invoice_number,
            "status": self.status,
            "notes": self.notes,
            "vat": self.vat,
            "total": self.total,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class ExpenseCRUD(CRUDBase[Expense, ExpenseCreateDTO, ExpenseUpdateDTO]):
    pass


class ExpenseRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = ExpenseCRUD(Expense)

    def list(self, tenant_id: int) -> list[Expense]:
        return list(self.crud.list(self.db))

    def get(self, tenant_id: int | UUID, expense_id: UUID) -> Expense | None:
        return self.crud.get(self.db, expense_id)

    def create(
        self,
        tenant_id: int | UUID,
        *,
        date,
        supplier_id: UUID | None,
        amount: float,
        concept: str | None,
        category: str | None = None,
        subcategory: str | None = None,
        payment_method: str | None = None,
        invoice_number: str | None = None,
        status: str | None = None,
        notes: str | None = None,
        vat: float | None = None,
        total: float | None = None,
        user_id: UUID | None = None,
    ) -> Expense:
        amount_value = float(amount or 0)
        vat_value = float(vat or 0)
        dto = ExpenseCreateDTO(
            date=date,
            supplier_id=supplier_id,
            amount=amount_value,
            concept=concept,
            category=category,
            subcategory=subcategory,
            payment_method=payment_method,
            invoice_number=invoice_number,
            status=status or "pending",
            notes=notes,
            vat=vat_value,
            total=float(total) if total is not None else (amount_value + vat_value),
            user_id=user_id,
        )
        return self.crud.create(self.db, dto, extra_fields={"tenant_id": tenant_id})

    def update(
        self,
        tenant_id: int | UUID,
        expense_id: UUID,
        *,
        date,
        supplier_id: UUID | None,
        amount: float,
        concept: str | None,
        category: str | None = None,
        subcategory: str | None = None,
        payment_method: str | None = None,
        invoice_number: str | None = None,
        status: str | None = None,
        notes: str | None = None,
        vat: float | None = None,
        total: float | None = None,
    ) -> Expense:
        amount_value = float(amount or 0)
        vat_value = float(vat or 0)
        dto = ExpenseUpdateDTO(
            date=date,
            supplier_id=supplier_id,
            amount=amount_value,
            concept=concept,
            category=category,
            subcategory=subcategory,
            payment_method=payment_method,
            invoice_number=invoice_number,
            status=status,
            notes=notes,
            vat=vat,
            total=float(total) if total is not None else (amount_value + vat_value),
        )
        obj = self.crud.update(self.db, expense_id, dto)
        if not obj:
            raise ValueError("Expense not found")
        return obj

    def delete(self, tenant_id: int | UUID, expense_id: UUID) -> None:
        ok = self.crud.delete(self.db, expense_id)
        if not ok:
            raise ValueError("Expense not found")
