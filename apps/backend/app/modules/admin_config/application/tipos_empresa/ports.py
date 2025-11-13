from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut


class TipoEmpresaRepo(Protocol):
    def list(self) -> Sequence[TipoEmpresaOut]: ...

    def create(self, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def get(self, id: int) -> TipoEmpresaOut | None: ...

    def update(self, id: int, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def delete(self, id: int) -> None: ...
