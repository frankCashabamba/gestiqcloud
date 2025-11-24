from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut
from app.modules.admin_config.application.tipos_empresa.ports import TipoCompanyRepo
from app.modules.shared.application.base import BaseUseCase


class ListarTiposEmpresa(BaseUseCase[TipoCompanyRepo]):
    def execute(self) -> Sequence[TipoEmpresaOut]:
        return list(self.repo.list())


class ObtenerTipoEmpresa(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str) -> TipoEmpresaOut:
        tipo = self.repo.get(id)
        if not tipo:
            raise ValueError("tipo_empresa_no_encontrado")
        return tipo


class CrearTipoEmpresa(BaseUseCase[TipoCompanyRepo]):
    def execute(self, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.create(data)


class ActualizarTipoEmpresa(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.update(id, data)


class EliminarTipoEmpresa(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str) -> None:
        self.repo.delete(id)
