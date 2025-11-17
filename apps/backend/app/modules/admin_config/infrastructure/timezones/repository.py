from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.empresa.empresa import RefTimezone as TimezoneORM
from app.modules.admin_config.application.timezones.dto import TimezoneIn, TimezoneOut
from app.modules.admin_config.application.timezones.ports import TimezoneRepo


class SqlAlchemyTimezoneRepo(TimezoneRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, t: TimezoneORM) -> TimezoneOut:
        return TimezoneOut(
            name=t.name,
            display_name=t.display_name,
            offset_minutes=t.offset_minutes,
            active=t.active,
        )

    def list(self) -> Sequence[TimezoneOut]:
        rows = self.db.query(TimezoneORM).order_by(TimezoneORM.name.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TimezoneIn) -> TimezoneOut:
        obj = TimezoneORM(
            name=data.name,
            display_name=data.display_name,
            offset_minutes=data.offset_minutes,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, name: str) -> TimezoneOut | None:
        obj = self.db.query(TimezoneORM).filter(TimezoneORM.name == name).first()
        return self._to_dto(obj) if obj else None

    def update(self, name: str, data: TimezoneIn) -> TimezoneOut:
        obj = self.db.query(TimezoneORM).filter(TimezoneORM.name == name).first()
        if not obj:
            raise ValueError("timezone_no_encontrado")
        obj.name = data.name
        obj.display_name = data.display_name
        obj.offset_minutes = data.offset_minutes
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, name: str) -> None:
        obj = self.db.query(TimezoneORM).filter(TimezoneORM.name == name).first()
        if not obj:
            raise ValueError("timezone_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
