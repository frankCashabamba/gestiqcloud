from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.company.company import Language as IdiomaORM
from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut
from app.modules.admin_config.application.idiomas.ports import IdiomaRepo


class SqlAlchemyIdiomaRepo(IdiomaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, i: IdiomaORM) -> IdiomaOut:
        return IdiomaOut(
            id=i.id,
            code=i.code,
            name=i.name,
            active=i.active,
        )

    def list(self) -> Sequence[IdiomaOut]:
        rows = self.db.query(IdiomaORM).order_by(IdiomaORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: IdiomaIn) -> IdiomaOut:
        obj = IdiomaORM(
            code=data.code,
            name=data.name,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> IdiomaOut | None:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: IdiomaIn) -> IdiomaOut:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        if not obj:
            raise ValueError("language_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        if not obj:
            raise ValueError("language_not_found")
        self.db.delete(obj)
        self.db.commit()
