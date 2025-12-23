from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.admin_config.application.sectores_plantilla.dto import (
    SectorPlantillaIn,
    SectorPlantillaOut,
)


class SectorPlantillaRepo(Protocol):
    def list(self) -> Sequence[SectorPlantillaOut]: ...

    def create(self, data: SectorPlantillaIn) -> SectorPlantillaOut: ...

    def get(self, id: UUID) -> SectorPlantillaOut | None: ...

    def update(self, id: UUID, data: SectorPlantillaIn) -> SectorPlantillaOut: ...

    def delete(self, id: UUID) -> None: ...
