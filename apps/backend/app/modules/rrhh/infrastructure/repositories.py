from app.core.crud_base import CRUDBase
from app.models.hr import Vacacion
from sqlalchemy.orm import Session


class VacacionCRUD(CRUDBase[Vacacion, "VacacionCreateDTO", "VacacionUpdateDTO"]):
    pass


class VacacionRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VacacionCRUD(Vacacion)

    def list(self) -> list[Vacacion]:
        return list(self.crud.list(self.db))

    def get(self, vid: int) -> Vacacion | None:
        return self.crud.get(self.db, vid)
