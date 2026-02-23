from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.unidades_medida.dto import (
    UnidadMedidaIn,
    UnidadMedidaOut,
)


class UnidadMedidaRepo(Protocol):
    def list(self) -> Sequence[UnidadMedidaOut]: ...
    def create(self, data: UnidadMedidaIn) -> UnidadMedidaOut: ...
    def get(self, id: int) -> UnidadMedidaOut | None: ...
    def update(self, id: int, data: UnidadMedidaIn) -> UnidadMedidaOut: ...
    def delete(self, id: int) -> None: ...
