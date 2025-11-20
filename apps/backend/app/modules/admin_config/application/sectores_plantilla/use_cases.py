from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.sectores_plantilla.dto import (
    SectorPlantillaIn,
    SectorPlantillaOut,
)
from app.modules.admin_config.application.sectores_plantilla.ports import SectorPlantillaRepo
from app.modules.shared.application.base import BaseUseCase


class ListarSectoresPlantilla(BaseUseCase[SectorPlantillaRepo]):
    def execute(self) -> Sequence[SectorPlantillaOut]:
        return list(self.repo.list())


class ObtenerSectorPlantilla(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int) -> SectorPlantillaOut:
        sector = self.repo.get(id)
        if not sector:
            raise ValueError("sector_no_encontrado")
        return sector


class CrearSectorPlantilla(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, data: SectorPlantillaIn) -> SectorPlantillaOut:
        return self.repo.create(data)


class ActualizarSectorPlantilla(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int, data: SectorPlantillaIn) -> SectorPlantillaOut:
        return self.repo.update(id, data)


class EliminarSectorPlantilla(BaseUseCase[SectorPlantillaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
