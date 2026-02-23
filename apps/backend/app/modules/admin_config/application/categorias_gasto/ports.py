from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.categorias_gasto.dto import (
    CategoriaGastoIn,
    CategoriaGastoOut,
)


class CategoriaGastoRepo(Protocol):
    def list(self) -> Sequence[CategoriaGastoOut]: ...
    def create(self, data: CategoriaGastoIn) -> CategoriaGastoOut: ...
    def get(self, id: int) -> CategoriaGastoOut | None: ...
    def update(self, id: int, data: CategoriaGastoIn) -> CategoriaGastoOut: ...
    def delete(self, id: int) -> None: ...
