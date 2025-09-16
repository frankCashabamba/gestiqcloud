from typing import List
from sqlalchemy.orm import Session
from .models import CajaMovimiento, BancoMovimiento


class CajaRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[CajaMovimiento]:
        return self.db.query(CajaMovimiento).order_by(CajaMovimiento.id.desc()).all()


class BancoRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[BancoMovimiento]:
        return self.db.query(BancoMovimiento).order_by(BancoMovimiento.id.desc()).all()

