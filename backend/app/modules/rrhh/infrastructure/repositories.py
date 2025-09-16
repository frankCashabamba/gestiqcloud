from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Vacacion


class VacacionRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[Vacacion]:
        return self.db.query(Vacacion).order_by(Vacacion.id.desc()).all()

    def get(self, vid: int) -> Optional[Vacacion]:
        return self.db.query(Vacacion).filter(Vacacion.id == vid).first()

