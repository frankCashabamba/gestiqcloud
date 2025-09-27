from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Venta
from app.core.crud_base import CRUDBase


class VentaCRUD(CRUDBase[Venta, "VentaCreateDTO", "VentaUpdateDTO"]):
    pass


class VentaRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VentaCRUD(Venta)

    def list(self) -> List[Venta]:
        return list(self.crud.list(self.db))

    def get(self, vid: int) -> Optional[Venta]:
        return self.crud.get(self.db, vid)

    def create(self, *, fecha, cliente_id: int | None, total: float, estado: str | None) -> Venta:
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

        dto = VentaCreateDTO(fecha=fecha, cliente_id=cliente_id, total=total, estado=estado)
        return self.crud.create(self.db, dto)

    def update(self, vid: int, *, fecha, cliente_id: int | None, total: float, estado: str | None) -> Venta:
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

        dto = VentaUpdateDTO(fecha=fecha, cliente_id=cliente_id, total=total, estado=estado)
        obj = self.crud.update(self.db, vid, dto)
        if not obj:
            raise ValueError("Venta no encontrada")
        return obj

    def delete(self, vid: int) -> None:
        ok = self.crud.delete(self.db, vid)
        if not ok:
            raise ValueError("Venta no encontrada")
