from dataclasses import dataclass

from app.core.crud_base import CRUDBase
from app.models.purchases import Purchase
from sqlalchemy.orm import Session


@dataclass
class PurchaseCreateDTO:
    tenant_id: int | None = None
    date: str | None = None
    supplier_id: int | None = None
    total: float | None = None
    status: str | None = None

    def model_dump(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "date": self.date,
            "supplier_id": self.supplier_id,
            "total": self.total,
            "status": self.status,
        }


@dataclass
class PurchaseUpdateDTO:
    date: str | None = None
    supplier_id: int | None = None
    total: float | None = None
    status: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "date": self.date,
            "supplier_id": self.supplier_id,
            "total": self.total,
            "status": self.status,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class PurchaseCRUD(CRUDBase[Purchase, PurchaseCreateDTO, PurchaseUpdateDTO]):
    pass


class PurchaseRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = PurchaseCRUD(Purchase)

    def list(self, tenant_id) -> list[Purchase]:
        return (
            self.db.query(Purchase)
            .filter(Purchase.tenant_id == tenant_id)
            .order_by(Purchase.date.desc())
            .all()
        )

    def get(self, tenant_id, cid) -> Purchase | None:
        return (
            self.db.query(Purchase)
            .filter(Purchase.tenant_id == tenant_id, Purchase.id == cid)
            .first()
        )

    def create(
        self,
        tenant_id,
        *,
        date,
        supplier_id: int | None,
        total: float,
        status: str | None,
    ) -> Purchase:
        dto = PurchaseCreateDTO(
            tenant_id=tenant_id,
            date=date,
            supplier_id=supplier_id,
            total=total,
            status=status,
        )
        return self.crud.create(self.db, dto)

    def update(
        self,
        tenant_id,
        cid,
        *,
        date,
        supplier_id: int | None,
        total: float,
        status: str | None,
    ) -> Purchase:
        dto = PurchaseUpdateDTO(date=date, supplier_id=supplier_id, total=total, status=status)
        obj = self.get(tenant_id, cid)
        if not obj:
            raise ValueError("Purchase not found")
        return self.crud.update(self.db, obj, dto)

    def delete(self, tenant_id, cid) -> None:
        obj = self.get(tenant_id, cid)
        if not obj:
            raise ValueError("Purchase not found")
        ok = self.crud.delete(self.db, cid)
        if not ok:
            raise ValueError("Purchase not found")
