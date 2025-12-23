from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company.company import BusinessCategory as TipoNegocioORM
from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn, TipoNegocioOut
from app.modules.admin_config.application.tipos_negocio.ports import TipoNegocioRepo


class SqlAlchemyTipoNegocioRepo(TipoNegocioRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, t: TipoNegocioORM) -> TipoNegocioOut:
        return TipoNegocioOut(
            id=t.id,
            name=t.name,
            description=t.description,
            active=t.active,
        )

    def list(self) -> Sequence[TipoNegocioOut]:
        rows = self.db.query(TipoNegocioORM).order_by(TipoNegocioORM.name.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TipoNegocioIn) -> TipoNegocioOut:
        obj = TipoNegocioORM(
            name=data.name,
            description=data.description,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: UUID) -> TipoNegocioOut | None:
        obj = self.db.query(TipoNegocioORM).filter(TipoNegocioORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: UUID, data: TipoNegocioIn) -> TipoNegocioOut:
        obj = self.db.query(TipoNegocioORM).filter(TipoNegocioORM.id == id).first()
        if not obj:
            raise ValueError("tipo_negocio_no_encontrado")
        obj.name = data.name
        obj.description = data.description
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: UUID) -> None:
        obj = self.db.query(TipoNegocioORM).filter(TipoNegocioORM.id == id).first()
        if not obj:
            raise ValueError("tipo_negocio_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
