from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.metodos_pago_plantilla.dto import (
    MetodoPagoPlantillaIn,
    MetodoPagoPlantillaOut,
)


class MetodoPagoPlantillaRepo(Protocol):
    def list(self) -> Sequence[MetodoPagoPlantillaOut]: ...
    def create(self, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut: ...
    def get(self, id: int) -> MetodoPagoPlantillaOut | None: ...
    def update(self, id: int, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut: ...
    def delete(self, id: int) -> None: ...
