from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.company.company import Currency as MonedaORM
from app.modules.admin_config.application.monedas.dto import MonedaIn, MonedaOut
from app.modules.admin_config.application.monedas.ports import MonedaRepo


class SqlAlchemyMonedaRepo(MonedaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: MonedaORM) -> MonedaOut:
        return MonedaOut(
            id=m.id,
            code=m.code,
            name=m.name,
            symbol=m.symbol,
            active=m.active,
        )

    def list(self) -> Sequence[MonedaOut]:
        rows = self.db.query(MonedaORM).order_by(MonedaORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: MonedaIn) -> MonedaOut:
        obj = MonedaORM(
            code=data.code,
            name=data.name,
            symbol=data.symbol,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> MonedaOut | None:
        obj = self.db.query(MonedaORM).filter(MonedaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: MonedaIn) -> MonedaOut:
        obj = self.db.query(MonedaORM).filter(MonedaORM.id == id).first()
        if not obj:
            raise ValueError("moneda_no_encontrada")
        obj.code = data.code
        obj.name = data.name
        obj.symbol = data.symbol
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(MonedaORM).filter(MonedaORM.id == id).first()
        if not obj:
            raise ValueError("moneda_no_encontrada")
        self.db.delete(obj)
        self.db.commit()
