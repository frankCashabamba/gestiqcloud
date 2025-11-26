from dataclasses import dataclass
from uuid import UUID, uuid4

from app.core.crud_base import CRUDBase
from app.models.sales import Sale
from app.models.tenant import Tenant
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class SaleCreateDTO:
    date: str | None = None
    customer_id: str | None = None
    total: float | None = None
    status: str | None = None

    def model_dump(self) -> dict:
        return {
            "date": self.date,
            "customer_id": self.customer_id,
            "total": self.total,
            "status": self.status,
        }


@dataclass
class SaleUpdateDTO:
    date: str | None = None
    customer_id: str | None = None
    total: float | None = None
    status: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "date": self.date,
            "customer_id": self.customer_id,
            "total": self.total,
            "status": self.status,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class SaleCRUD(CRUDBase[Sale, SaleCreateDTO, SaleUpdateDTO]):
    pass


UUIDLike = str | UUID


def _uuid_str(value: UUIDLike | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _uuid_obj(value: UUIDLike | None) -> UUID | None:
    """Convert string or UUID to UUID object."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


class SaleRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = SaleCRUD(Sale)

    def list(self) -> list[Sale]:
        return list(self.crud.list(self.db))

    def get(self, vid: UUIDLike) -> Sale | None:
        return self.crud.get(self.db, str(vid))

    def create(
        self, *, date, customer_id: UUIDLike | None, total: float, status: str | None
    ) -> Sale:
        tenant_id = self._resolve_tenant_id()
        user_id = self._resolve_user_id()
        dto = SaleCreateDTO(
            date=date, customer_id=_uuid_str(customer_id), total=total, status=status
        )
        return self.crud.create(
            self.db,
            dto,
            extra_fields={"tenant_id": _uuid_obj(tenant_id), "user_id": _uuid_obj(user_id)},
        )

    def update(
        self,
        vid: UUIDLike,
        *,
        date,
        customer_id: UUIDLike | None,
        total: float,
        status: str | None,
    ) -> Sale:
        dto = SaleUpdateDTO(
            date=date, customer_id=_uuid_str(customer_id), total=total, status=status
        )
        obj = self.crud.update(self.db, str(vid), dto)
        if not obj:
            raise ValueError("Sale not found")
        return obj

    def delete(self, vid: UUIDLike) -> None:
        ok = self.crud.delete(self.db, str(vid))
        if not ok:
            raise ValueError("Sale not found")

    def _resolve_tenant_id(self) -> str:
        tid = self.db.info.get("tenant_id")
        if tid:
            return str(tid)
        tenant_id = self.db.scalar(select(Tenant.id).limit(1))
        if tenant_id:
            return str(tenant_id)
        raise ValueError("tenant_id_missing")

    def _resolve_user_id(self) -> str:
        uid = self.db.info.get("user_id")
        if uid:
            return str(uid)
        return str(uuid4())
