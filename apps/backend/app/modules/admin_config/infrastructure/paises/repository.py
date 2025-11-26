from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.company.company import Country as PaisORM
from app.modules.admin_config.application.paises.dto import PaisIn, PaisOut
from app.modules.admin_config.application.paises.ports import PaisRepo


class SqlAlchemyPaisRepo(PaisRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, p: PaisORM) -> PaisOut:
        return PaisOut(
            id=p.id,
            code=p.code,
            name=p.name,
            active=p.active,
        )

    def list(self) -> Sequence[PaisOut]:
        rows = self.db.query(PaisORM).order_by(PaisORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: PaisIn) -> PaisOut:
        obj = PaisORM(
            code=data.code,
            name=data.name,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> PaisOut | None:
        obj = self.db.query(PaisORM).filter(PaisORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: PaisIn) -> PaisOut:
        obj = self.db.query(PaisORM).filter(PaisORM.id == id).first()
        if not obj:
            raise ValueError("country_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(PaisORM).filter(PaisORM.id == id).first()
        if not obj:
            raise ValueError("country_not_found")
        self.db.delete(obj)
        self.db.commit()
