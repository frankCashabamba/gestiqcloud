from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Vacacion
from app.core.crud_base import CRUDBase


class VacacionCRUD(CRUDBase[Vacacion, "VacacionCreateDTO", "VacacionUpdateDTO"]):
    pass


class VacacionRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VacacionCRUD(Vacacion)

    def list(self) -> List[Vacacion]:
        return list(self.crud.list(self.db))

    def get(self, vid: int) -> Optional[Vacacion]:
        return self.crud.get(self.db, vid)
