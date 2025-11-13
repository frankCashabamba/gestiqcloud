from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.sectores_plantilla.dto import SectorPlantillaIn, SectorPlantillaOut


class SectorPlantillaRepo(Protocol):
    def list(self) -> Sequence[SectorPlantillaOut]: ...

    def create(self, data: SectorPlantillaIn) -> SectorPlantillaOut: ...

    def get(self, id: int) -> Optional[SectorPlantillaOut]: ...

    def update(self, id: int, data: SectorPlantillaIn) -> SectorPlantillaOut: ...

    def delete(self, id: int) -> None: ...
