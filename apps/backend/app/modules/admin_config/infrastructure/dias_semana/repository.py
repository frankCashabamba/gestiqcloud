from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.company.company import Weekday as DiaSemanaORM
from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn, DiaSemanaOut
from app.modules.admin_config.application.dias_semana.ports import DiaSemanaRepo


class SqlAlchemyDiaSemanaRepo(DiaSemanaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, d: DiaSemanaORM) -> DiaSemanaOut:
        return DiaSemanaOut(
            id=d.id,
            code=d.key,
            name=d.name,
            order=d.order,
        )

    def list(self) -> Sequence[DiaSemanaOut]:
        rows = self.db.query(DiaSemanaORM).order_by(DiaSemanaORM.order.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: DiaSemanaIn) -> DiaSemanaOut:
        obj = DiaSemanaORM(
            key=data.code,
            name=data.name,
            order=data.order,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> DiaSemanaOut | None:
        obj = self.db.query(DiaSemanaORM).filter(DiaSemanaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: DiaSemanaIn) -> DiaSemanaOut:
        obj = self.db.query(DiaSemanaORM).filter(DiaSemanaORM.id == id).first()
        if not obj:
            raise ValueError("day_not_found")
        obj.key = data.code
        obj.name = data.name
        obj.order = data.order
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(DiaSemanaORM).filter(DiaSemanaORM.id == id).first()
        if not obj:
            raise ValueError("day_not_found")
        self.db.delete(obj)
        self.db.commit()
