from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crud_base import CRUDBase
from app.models.expenses import Gasto


@dataclass
class GastoCreateDTO:
    fecha: str | None = None
    proveedor_id: int | None = None
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self) -> dict:
        return {
            "fecha": self.fecha,
            "proveedor_id": self.proveedor_id,
            "monto": self.monto,
            "concepto": self.concepto,
        }


@dataclass
class GastoUpdateDTO:
    fecha: str | None = None
    proveedor_id: int | None = None
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "fecha": self.fecha,
            "proveedor_id": self.proveedor_id,
            "monto": self.monto,
            "concepto": self.concepto,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class GastoCRUD(CRUDBase[Gasto, GastoCreateDTO, GastoUpdateDTO]):
    pass


class GastoRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = GastoCRUD(Gasto)

    def list(self) -> list[Gasto]:
        return list(self.crud.list(self.db))

    def get(self, gid: int) -> Gasto | None:
        return self.crud.get(self.db, gid)

    def create(
        self, *, fecha, proveedor_id: int | None, monto: float, concepto: str | None
    ) -> Gasto:
        dto = GastoCreateDTO(fecha=fecha, proveedor_id=proveedor_id, monto=monto, concepto=concepto)
        return self.crud.create(self.db, dto)

    def update(
        self,
        gid: int,
        *,
        fecha,
        proveedor_id: int | None,
        monto: float,
        concepto: str | None,
    ) -> Gasto:
        dto = GastoUpdateDTO(fecha=fecha, proveedor_id=proveedor_id, monto=monto, concepto=concepto)
        obj = self.crud.update(self.db, gid, dto)
        if not obj:
            raise ValueError("Gasto no encontrado")
        return obj

    def delete(self, gid: int) -> None:
        ok = self.crud.delete(self.db, gid)
        if not ok:
            raise ValueError("Gasto no encontrado")
