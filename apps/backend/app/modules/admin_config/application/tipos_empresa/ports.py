from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut


class TipoEmpresaRepo(Protocol):
    def list(self) -> Sequence[TipoEmpresaOut]: ...

    def create(self, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def get(self, id: int) -> Optional[TipoEmpresaOut]: ...

    def update(self, id: int, data: TipoEmpresaIn) -> TipoEmpresaOut: ...

    def delete(self, id: int) -> None: ...
