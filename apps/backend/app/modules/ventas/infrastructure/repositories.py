from typing import Union
from uuid import UUID, uuid4

from app.core.crud_base import CRUDBase
from app.models.sales import Venta
from app.models.tenant import Tenant
from sqlalchemy import select
from sqlalchemy.orm import Session


class VentaCRUD(CRUDBase[Venta, "VentaCreateDTO", "VentaUpdateDTO"]):
    pass


UUIDLike = Union[str, UUID]


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


class VentaRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VentaCRUD(Venta)

    def list(self) -> list[Venta]:
        return list(self.crud.list(self.db))

    def get(self, vid: UUIDLike) -> Venta | None:
        return self.crud.get(self.db, str(vid))

    def create(
        self, *, fecha, cliente_id: UUIDLike | None, total: float, estado: str | None
    ) -> Venta:
        class VentaCreateDTO:
            def __init__(self, **kw):
                self.fecha = kw.get("fecha")
                self.cliente_id = kw.get("cliente_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self):
                return {
                    "fecha": self.fecha,
                    "cliente_id": self.cliente_id,
                    "total": self.total,
                    "estado": self.estado,
                }

        tenant_id = self._resolve_tenant_id()
        user_id = self._resolve_user_id()
        dto = VentaCreateDTO(
            fecha=fecha, cliente_id=_uuid_str(cliente_id), total=total, estado=estado
        )
        return self.crud.create(
            self.db,
            dto,
            extra_fields={"tenant_id": _uuid_obj(tenant_id), "usuario_id": _uuid_obj(user_id)},
        )

    def update(
        self,
        vid: UUIDLike,
        *,
        fecha,
        cliente_id: UUIDLike | None,
        total: float,
        estado: str | None,
    ) -> Venta:
        class VentaUpdateDTO:
            def __init__(self, **kw):
                self.fecha = kw.get("fecha")
                self.cliente_id = kw.get("cliente_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "fecha": self.fecha,
                    "cliente_id": self.cliente_id,
                    "total": self.total,
                    "estado": self.estado,
                }
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = VentaUpdateDTO(
            fecha=fecha, cliente_id=_uuid_str(cliente_id), total=total, estado=estado
        )
        obj = self.crud.update(self.db, str(vid), dto)
        if not obj:
            raise ValueError("Venta no encontrada")
        return obj

    def delete(self, vid: UUIDLike) -> None:
        ok = self.crud.delete(self.db, str(vid))
        if not ok:
            raise ValueError("Venta no encontrada")

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
