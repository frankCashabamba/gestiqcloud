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
            dia_id=h.weekday_id,
            inicio=h.start_time,
            fin=h.end_time,
        )

    def list(self) -> Sequence[HorarioAtencionOut]:
        rows = (
            self.db.query(HorarioAtencionORM)
            .order_by(HorarioAtencionORM.dia_id.asc(), HorarioAtencionORM.inicio.asc())
            .all()
        )
        return [self._to_dto(r) for r in rows]

    def create(self, data: HorarioAtencionIn) -> HorarioAtencionOut:
        obj = HorarioAtencionORM(
            weekday_id=data.dia_id,
            start_time=data.inicio,
            end_time=data.fin,
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
        obj.weekday_id = data.dia_id
        obj.start_time = data.inicio
        obj.end_time = data.fin
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
