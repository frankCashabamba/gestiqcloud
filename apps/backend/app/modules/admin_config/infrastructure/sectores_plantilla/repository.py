from __future__ import annotations

from collections.abc import Sequence

from app.models.empresa.empresa import SectorPlantilla as SectorPlantillaORM
from app.modules.admin_config.application.sectores_plantilla.dto import (
    SectorPlantillaIn,
    SectorPlantillaOut,
)
from app.modules.admin_config.application.sectores_plantilla.ports import SectorPlantillaRepo
from sqlalchemy.orm import Session


class SqlAlchemySectorPlantillaRepo(SectorPlantillaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, s: SectorPlantillaORM) -> SectorPlantillaOut:
        return SectorPlantillaOut(
            id=s.id,
            sector_name=s.sector_name,
            business_type_id=s.business_type_id,
            business_category_id=s.business_category_id,
            template_config=s.template_config,
            active=s.active,
            created_at=s.created_at,
        )

    def list(self) -> Sequence[SectorPlantillaOut]:
        rows = (
            self.db.query(SectorPlantillaORM).order_by(SectorPlantillaORM.sector_name.asc()).all()
        )
        return [self._to_dto(r) for r in rows]

    def create(self, data: SectorPlantillaIn) -> SectorPlantillaOut:
        obj = SectorPlantillaORM(
            sector_name=data.sector_name,
            business_type_id=data.business_type_id,
            business_category_id=data.business_category_id,
            template_config=data.template_config,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> SectorPlantillaOut | None:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: SectorPlantillaIn) -> SectorPlantillaOut:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("sector_no_encontrado")
        obj.sector_name = data.sector_name
        obj.business_type_id = data.business_type_id
        obj.business_category_id = data.business_category_id
        obj.template_config = data.template_config
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("sector_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
