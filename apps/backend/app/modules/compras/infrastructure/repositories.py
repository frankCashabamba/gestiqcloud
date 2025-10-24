from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Compra
from app.core.crud_base import CRUDBase


class CompraCRUD(CRUDBase[Compra, "CompraCreateDTO", "CompraUpdateDTO"]):
    pass


class CompraRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = CompraCRUD(Compra)

    def list(self) -> List[Compra]:
        return list(self.crud.list(self.db))

    def get(self, cid: int) -> Optional[Compra]:
        return self.crud.get(self.db, cid)

    def create(self, *, fecha, proveedor_id: int | None, total: float, estado: str | None) -> Compra:
        class CompraCreateDTO:
            def __init__(self, **kw):
                self.fecha = kw.get("fecha")
                self.proveedor_id = kw.get("proveedor_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self):
                return {
                    "fecha": self.fecha,
                    "proveedor_id": self.proveedor_id,
                    "total": self.total,
                    "estado": self.estado,
                }

        dto = CompraCreateDTO(fecha=fecha, proveedor_id=proveedor_id, total=total, estado=estado)
        return self.crud.create(self.db, dto)

    def update(self, cid: int, *, fecha, proveedor_id: int | None, total: float, estado: str | None) -> Compra:
        class CompraUpdateDTO:
            def __init__(self, **kw):
                self.fecha = kw.get("fecha")
                self.proveedor_id = kw.get("proveedor_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "fecha": self.fecha,
                    "proveedor_id": self.proveedor_id,
                    "total": self.total,
                    "estado": self.estado,
                }
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = CompraUpdateDTO(fecha=fecha, proveedor_id=proveedor_id, total=total, estado=estado)
        obj = self.crud.update(self.db, cid, dto)
        if not obj:
            raise ValueError("Compra no encontrada")
        return obj

    def delete(self, cid: int) -> None:
        ok = self.crud.delete(self.db, cid)
        if not ok:
            raise ValueError("Compra no encontrada")
