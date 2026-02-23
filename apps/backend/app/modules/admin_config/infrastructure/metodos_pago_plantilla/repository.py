from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.core.global_catalogs import PaymentMethodTemplate as MetodoPagoPlantillaORM
from app.modules.admin_config.application.metodos_pago_plantilla.dto import MetodoPagoPlantillaIn, MetodoPagoPlantillaOut
from app.modules.admin_config.application.metodos_pago_plantilla.ports import MetodoPagoPlantillaRepo


class SqlAlchemyMetodoPagoPlantillaRepo(MetodoPagoPlantillaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: MetodoPagoPlantillaORM) -> MetodoPagoPlantillaOut:
        return MetodoPagoPlantillaOut(
            id=m.id,
            code=m.code,
            name=m.name,
            description=m.description,
            active=m.active,
        )

    def list(self) -> Sequence[MetodoPagoPlantillaOut]:
        rows = self.db.query(MetodoPagoPlantillaORM).order_by(MetodoPagoPlantillaORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut:
        obj = MetodoPagoPlantillaORM(
            code=data.code,
            name=data.name,
            description=data.description,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> MetodoPagoPlantillaOut | None:
        obj = self.db.query(MetodoPagoPlantillaORM).filter(MetodoPagoPlantillaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut:
        obj = self.db.query(MetodoPagoPlantillaORM).filter(MetodoPagoPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("payment_template_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.description = data.description
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(MetodoPagoPlantillaORM).filter(MetodoPagoPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("payment_template_not_found")
        self.db.delete(obj)
        self.db.commit()
