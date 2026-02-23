from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.tipos_impuesto.dto import (
    TipoImpuestoIn,
    TipoImpuestoOut,
)


class TipoImpuestoRepo(Protocol):
    def list(self) -> Sequence[TipoImpuestoOut]: ...
    def create(self, data: TipoImpuestoIn) -> TipoImpuestoOut: ...
    def get(self, id: str) -> TipoImpuestoOut | None: ...
    def update(self, id: str, data: TipoImpuestoIn) -> TipoImpuestoOut: ...
    def delete(self, id: str) -> None: ...
