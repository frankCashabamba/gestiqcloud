from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn, TipoNegocioOut


class TipoNegocioRepo(Protocol):
    def list(self) -> Sequence[TipoNegocioOut]: ...

    def create(self, data: TipoNegocioIn) -> TipoNegocioOut: ...

    def get(self, id: UUID) -> TipoNegocioOut | None: ...

    def update(self, id: UUID, data: TipoNegocioIn) -> TipoNegocioOut: ...

    def delete(self, id: UUID) -> None: ...
