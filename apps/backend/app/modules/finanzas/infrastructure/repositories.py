from app.core.crud_base import CRUDBase
from app.models.finance import BancoMovimiento, CajaMovimiento
from sqlalchemy.orm import Session


class CajaCRUD(CRUDBase[CajaMovimiento, "CajaCreateDTO", "CajaUpdateDTO"]):
    pass


class BancoCRUD(CRUDBase[BancoMovimiento, "BancoCreateDTO", "BancoUpdateDTO"]):
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
