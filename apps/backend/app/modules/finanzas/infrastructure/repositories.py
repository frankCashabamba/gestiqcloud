from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.finance import CajaMovimiento, BancoMovimiento
from app.core.crud_base import CRUDBase


class CajaCRUD(CRUDBase[CajaMovimiento, "CajaCreateDTO", "CajaUpdateDTO"]):
    pass


class BancoCRUD(CRUDBase[BancoMovimiento, "BancoCreateDTO", "BancoUpdateDTO"]):
    pass


class CajaRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = CajaCRUD(CajaMovimiento)

    def list(self) -> List[CajaMovimiento]:
        return list(self.crud.list(self.db))

    def get(self, mid: int) -> Optional[CajaMovimiento]:
        return self.crud.get(self.db, mid)


class BancoRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = BancoCRUD(BancoMovimiento)

    def list(self) -> List[BancoMovimiento]:
        return list(self.crud.list(self.db))

    def get(self, mid: int) -> Optional[BancoMovimiento]:
        return self.crud.get(self.db, mid)
