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

    def model_dump(self) -> dict:
        return {
            "date": self.date,
            "supplier_id": self.supplier_id,
            "amount": self.amount,
            "concept": self.concept,
        }


@dataclass
class ExpenseUpdateDTO:
    date: str | None = None
    supplier_id: UUID | None = None
    amount: float | None = None
    concept: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "date": self.date,
            "supplier_id": self.supplier_id,
            "amount": self.amount,
            "concept": self.concept,
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
        self, tenant_id: int | UUID, *, date, supplier_id: UUID | None, amount: float, concept: str | None
    ) -> Expense:
        dto = ExpenseCreateDTO(date=date, supplier_id=supplier_id, amount=amount, concept=concept)
        return self.crud.create(self.db, dto)

    def update(
        self,
        tenant_id: int | UUID,
        expense_id: UUID,
        *,
        date,
        supplier_id: UUID | None,
        amount: float,
        concept: str | None,
    ) -> Expense:
        dto = ExpenseUpdateDTO(date=date, supplier_id=supplier_id, amount=amount, concept=concept)
        obj = self.crud.update(self.db, expense_id, dto)
        if not obj:
            raise ValueError("Expense not found")
        return obj

    def delete(self, tenant_id: int | UUID, expense_id: UUID) -> None:
        ok = self.crud.delete(self.db, expense_id)
        if not ok:
            raise ValueError("Expense not found")
