from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crud_base import CRUDBase
from app.models.hr import Vacacion


@dataclass
class VacacionCreateDTO:
    empleado_id: int | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    dias: int | None = None

    def model_dump(self) -> dict:
        return {
            "empleado_id": self.empleado_id,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "dias": self.dias,
        }


@dataclass
class VacacionUpdateDTO:
    empleado_id: int | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    dias: int | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "empleado_id": self.empleado_id,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "dias": self.dias,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class VacacionCRUD(CRUDBase[Vacacion, VacacionCreateDTO, VacacionUpdateDTO]):
    pass


class VacacionRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = VacacionCRUD(Vacacion)

    def list(self) -> list[Vacacion]:
        return list(self.crud.list(self.db))

    def get(self, vid: int) -> Vacacion | None:
        return self.crud.get(self.db, vid)
