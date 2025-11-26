from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.sectores_plantilla.dto import (
    SectorPlantillaIn,
    SectorPlantillaOut,
)
from app.modules.admin_config.application.sectores_plantilla.ports import SectorPlantillaRepo
from app.modules.shared.application.base import BaseUseCase


class ListTemplateSectors(BaseUseCase[SectorPlantillaRepo]):
    def execute(self) -> Sequence[SectorPlantillaOut]:
        return list(self.repo.list())


class GetTemplateSector(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int) -> SectorPlantillaOut:
        sector = self.repo.get(id)
        if not sector:
            raise ValueError("sector_not_found")
        return sector


class CreateTemplateSector(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, data: SectorPlantillaIn) -> SectorPlantillaOut:
        return self.repo.create(data)


class UpdateTemplateSector(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int, data: SectorPlantillaIn) -> SectorPlantillaOut:
        return self.repo.update(id, data)


class DeleteTemplateSector(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
