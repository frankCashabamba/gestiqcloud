from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.tipos_documento.dto import (
    TipoDocumentoIn,
    TipoDocumentoOut,
)


class TipoDocumentoRepo(Protocol):
    def list(self) -> Sequence[TipoDocumentoOut]: ...
    def create(self, data: TipoDocumentoIn) -> TipoDocumentoOut: ...
    def get(self, id: int) -> TipoDocumentoOut | None: ...
    def update(self, id: int, data: TipoDocumentoIn) -> TipoDocumentoOut: ...
    def delete(self, id: int) -> None: ...
