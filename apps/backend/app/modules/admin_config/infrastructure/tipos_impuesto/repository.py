from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.core.country_catalogs import CountryTaxCode as TipoImpuestoORM
from app.modules.admin_config.application.tipos_impuesto.dto import TipoImpuestoIn, TipoImpuestoOut
from app.modules.admin_config.application.tipos_impuesto.ports import TipoImpuestoRepo


class SqlAlchemyTipoImpuestoRepo(TipoImpuestoRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: TipoImpuestoORM) -> TipoImpuestoOut:
        return TipoImpuestoOut(
            id=str(m.id),
            country_code=m.country_code,
            code=m.code,
            name=m.name,
            rate_default=float(m.rate_default) if m.rate_default is not None else None,
            active=m.active,
        )

    def list(self) -> Sequence[TipoImpuestoOut]:
        rows = self.db.query(TipoImpuestoORM).order_by(TipoImpuestoORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TipoImpuestoIn) -> TipoImpuestoOut:
        obj = TipoImpuestoORM(
            country_code=data.country_code,
            code=data.code,
            name=data.name,
            rate_default=data.rate_default,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: str) -> TipoImpuestoOut | None:
        obj = self.db.query(TipoImpuestoORM).filter(TipoImpuestoORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: str, data: TipoImpuestoIn) -> TipoImpuestoOut:
        obj = self.db.query(TipoImpuestoORM).filter(TipoImpuestoORM.id == id).first()
        if not obj:
            raise ValueError("tax_type_not_found")
        obj.country_code = data.country_code
        obj.code = data.code
        obj.name = data.name
        obj.rate_default = data.rate_default
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: str) -> None:
        obj = self.db.query(TipoImpuestoORM).filter(TipoImpuestoORM.id == id).first()
        if not obj:
            raise ValueError("tax_type_not_found")
        self.db.delete(obj)
        self.db.commit()
