from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut


class TipoCompanyRepo(Protocol):
    def list(self) -> Sequence[TipoEmpresaOut]: ...

    def create(self, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def get(self, id: UUID | str) -> TipoEmpresaOut | None: ...

    def update(self, id: UUID | str, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def delete(self, id: UUID | str) -> None: ...
