from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.core.global_catalogs import UnitOfMeasure as UnidadMedidaORM
from app.modules.admin_config.application.unidades_medida.dto import UnidadMedidaIn, UnidadMedidaOut
from app.modules.admin_config.application.unidades_medida.ports import UnidadMedidaRepo


class SqlAlchemyUnidadMedidaRepo(UnidadMedidaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: UnidadMedidaORM) -> UnidadMedidaOut:
        return UnidadMedidaOut(
            id=m.id,
            code=m.code,
            name=m.name,
            abbreviation=m.abbreviation,
            active=m.active,
        )

    def list(self) -> Sequence[UnidadMedidaOut]:
        rows = self.db.query(UnidadMedidaORM).order_by(UnidadMedidaORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: UnidadMedidaIn) -> UnidadMedidaOut:
        obj = UnidadMedidaORM(
            code=data.code,
            name=data.name,
            abbreviation=data.abbreviation,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> UnidadMedidaOut | None:
        obj = self.db.query(UnidadMedidaORM).filter(UnidadMedidaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: UnidadMedidaIn) -> UnidadMedidaOut:
        obj = self.db.query(UnidadMedidaORM).filter(UnidadMedidaORM.id == id).first()
        if not obj:
            raise ValueError("unit_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.abbreviation = data.abbreviation
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(UnidadMedidaORM).filter(UnidadMedidaORM.id == id).first()
        if not obj:
            raise ValueError("unit_not_found")
        self.db.delete(obj)
        self.db.commit()
