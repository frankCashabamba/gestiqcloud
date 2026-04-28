from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.core.crud_base import CRUDBase
from app.models.purchases import Purchase, PurchaseLine


@dataclass
class PurchaseCreateDTO:
    tenant_id: UUID | str | None = None
    date: str | None = None
    supplier_id: UUID | str | None = None
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
            .options(joinedload(Purchase.supplier))
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
        supplier_id: str | None,
        total: float,
        status: str | None,
        lines: list | None = None,
        subtotal: float | None = None,
        taxes: float | None = None,
        notes: str | None = None,
        delivery_date=None,
        user_id=None,
    ) -> Purchase:
        number = self._next_number(tenant_id)
        purchase = Purchase(
            tenant_id=tenant_id,
            number=number,
            date=date,
            supplier_id=supplier_id,
            subtotal=subtotal or 0,
            taxes=taxes or 0,
            total=total or 0,
            status=status or "draft",
            notes=notes,
            delivery_date=delivery_date,
            user_id=user_id,
        )
        try:
            self.db.add(purchase)
            self.db.flush()

            for line in lines or []:
                quantity = float(getattr(line, "quantity", 0) or 0)
                unit_price = float(getattr(line, "unit_price", 0) or 0)
                line_total = float(getattr(line, "subtotal", 0) or 0) or quantity * unit_price
                self.db.add(
                    PurchaseLine(
                        purchase_id=purchase.id,
                        product_id=getattr(line, "product_id", None),
                        quantity=quantity,
                        unit_price=unit_price,
                        tax_rate=0,
                        total=line_total,
                    )
                )
            self.db.commit()
            self.db.refresh(purchase)
        except Exception:
            self.db.rollback()
            raise
        return purchase

    def _next_number(self, tenant_id) -> str:
        prefix = "PO-"
        last = (
            self.db.query(Purchase.number)
            .filter(Purchase.tenant_id == tenant_id, Purchase.number.like(f"{prefix}%"))
            .order_by(Purchase.number.desc())
            .first()
        )
        if not last or not last[0]:
            return f"{prefix}000001"
        try:
            return f"{prefix}{int(str(last[0]).split('-')[-1]) + 1:06d}"
        except ValueError:
            return f"{prefix}000001"

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
