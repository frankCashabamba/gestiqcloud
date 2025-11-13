from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.sales import Venta
from app.core.crud_base import CRUDBase


class VentaCRUD(CRUDBase[Venta, "VentaCreateDTO", "VentaUpdateDTO"]):
    pass


UUIDLike = Union[str, UUID]


def _uuid_str(value: UUIDLike | None) -> Optional[str]:
    if value is None:
        return None
    return str(value)


class VentaRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VentaCRUD(Venta)

    def list(self) -> List[Venta]:
        return list(self.crud.list(self.db))

    def get(self, vid: UUIDLike) -> Optional[Venta]:
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

        dto = VentaCreateDTO(
            fecha=fecha, cliente_id=_uuid_str(cliente_id), total=total, estado=estado
        )
        return self.crud.create(self.db, dto)

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
                return {
                    k: v for k, v in d.items() if not exclude_unset or v is not None
                }

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
