from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.company.company import BusinessHours as HorarioAtencionORM
from app.modules.admin_config.application.horarios_atencion.dto import (
    HorarioAtencionIn,
    HorarioAtencionOut,
)
from app.modules.admin_config.application.horarios_atencion.ports import HorarioAtencionRepo


class SqlAlchemyHorarioAtencionRepo(HorarioAtencionRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, h: HorarioAtencionORM) -> HorarioAtencionOut:
        return HorarioAtencionOut(
            id=h.id,
            weekday_id=h.weekday_id,
            start_time=h.start_time,
            end_time=h.end_time,
        )

    def list(self) -> Sequence[HorarioAtencionOut]:
        rows = (
            self.db.query(HorarioAtencionORM)
            .order_by(HorarioAtencionORM.weekday_id.asc(), HorarioAtencionORM.start_time.asc())
            .all()
        )
        return [self._to_dto(r) for r in rows]

    def create(self, data: HorarioAtencionIn) -> HorarioAtencionOut:
        obj = HorarioAtencionORM(
            weekday_id=data.weekday_id,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> HorarioAtencionOut | None:
        obj = self.db.query(HorarioAtencionORM).filter(HorarioAtencionORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: HorarioAtencionIn) -> HorarioAtencionOut:
        obj = self.db.query(HorarioAtencionORM).filter(HorarioAtencionORM.id == id).first()
        if not obj:
            raise ValueError("horario_no_encontrado")
        obj.weekday_id = data.weekday_id
        obj.start_time = data.start_time
        obj.end_time = data.end_time
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(HorarioAtencionORM).filter(HorarioAtencionORM.id == id).first()
        if not obj:
            raise ValueError("horario_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
