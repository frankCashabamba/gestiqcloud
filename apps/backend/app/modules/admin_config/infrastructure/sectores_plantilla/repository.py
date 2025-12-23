from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company.company import SectorTemplate as SectorPlantillaORM
from app.modules.admin_config.application.sectores_plantilla.dto import (
    SectorPlantillaIn,
    SectorPlantillaOut,
)
from app.modules.admin_config.application.sectores_plantilla.ports import SectorPlantillaRepo


class SqlAlchemySectorPlantillaRepo(SectorPlantillaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, s: SectorPlantillaORM) -> SectorPlantillaOut:
        return SectorPlantillaOut(
            id=s.id,
            name=s.name,
            code=s.code,
            description=s.description,
            template_config=s.template_config,
            active=s.active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            config_version=getattr(s, "config_version", None),
        )

    def list(self) -> Sequence[SectorPlantillaOut]:
        rows = self.db.query(SectorPlantillaORM).order_by(SectorPlantillaORM.name.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: SectorPlantillaIn) -> SectorPlantillaOut:
        obj = SectorPlantillaORM(
            name=data.name,
            code=data.code,
            description=data.description,
            template_config=data.template_config,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: UUID) -> SectorPlantillaOut | None:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: UUID, data: SectorPlantillaIn) -> SectorPlantillaOut:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("sector_no_encontrado")
        obj.name = data.name
        obj.code = data.code
        obj.description = data.description
        obj.template_config = data.template_config
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: UUID) -> None:
        obj = self.db.query(SectorPlantillaORM).filter(SectorPlantillaORM.id == id).first()
        if not obj:
            raise ValueError("sector_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
