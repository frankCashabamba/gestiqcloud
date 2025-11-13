from __future__ import annotations

from collections.abc import Sequence

from app.models.empresa.empresa import RefLocale as LocaleORM
from app.modules.admin_config.application.locales.dto import LocaleIn, LocaleOut
from app.modules.admin_config.application.locales.ports import LocaleRepo
from sqlalchemy.orm import Session


class SqlAlchemyLocaleRepo(LocaleRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, l: LocaleORM) -> LocaleOut:
        return LocaleOut(
            code=l.code,
            name=l.name,
            active=l.active,
        )

    def list(self) -> Sequence[LocaleOut]:
        rows = self.db.query(LocaleORM).order_by(LocaleORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: LocaleIn) -> LocaleOut:
        obj = LocaleORM(
            code=data.code,
            name=data.name,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, code: str) -> LocaleOut | None:
        obj = self.db.query(LocaleORM).filter(LocaleORM.code == code).first()
        return self._to_dto(obj) if obj else None

    def update(self, code: str, data: LocaleIn) -> LocaleOut:
        obj = self.db.query(LocaleORM).filter(LocaleORM.code == code).first()
        if not obj:
            raise ValueError("locale_no_encontrado")
        obj.code = data.code
        obj.name = data.name
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, code: str) -> None:
        obj = self.db.query(LocaleORM).filter(LocaleORM.code == code).first()
        if not obj:
            raise ValueError("locale_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
