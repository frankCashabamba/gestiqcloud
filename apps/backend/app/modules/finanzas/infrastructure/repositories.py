from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crud_base import CRUDBase
from app.models.finance import BancoMovimiento, CajaMovimiento


@dataclass
class CajaCreateDTO:
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self) -> dict:
        return {"monto": self.monto, "concepto": self.concepto}


@dataclass
class CajaUpdateDTO:
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {"monto": self.monto, "concepto": self.concepto}
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


@dataclass
class BancoCreateDTO:
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self) -> dict:
        return {"monto": self.monto, "concepto": self.concepto}


@dataclass
class BancoUpdateDTO:
    monto: float | None = None
    concepto: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {"monto": self.monto, "concepto": self.concepto}
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class CajaCRUD(CRUDBase[CajaMovimiento, CajaCreateDTO, CajaUpdateDTO]):
    pass


class BancoCRUD(CRUDBase[BancoMovimiento, BancoCreateDTO, BancoUpdateDTO]):
    pass


class CajaRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = CajaCRUD(CajaMovimiento)

    def list(self) -> list[CajaMovimiento]:
        return list(self.crud.list(self.db))

    def get(self, mid: int) -> CajaMovimiento | None:
        return self.crud.get(self.db, mid)


class BancoRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = BancoCRUD(BancoMovimiento)

    def list(self) -> list[BancoMovimiento]:
        return list(self.crud.list(self.db))

    def get(self, mid: int) -> BancoMovimiento | None:
        return self.crud.get(self.db, mid)
