from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut
from app.modules.admin_config.application.tipos_empresa.ports import TipoEmpresaRepo
from app.modules.shared.application.base import BaseUseCase


class ListarTiposEmpresa(BaseUseCase[TipoEmpresaRepo]):
    def execute(self) -> Sequence[TipoEmpresaOut]:
        return list(self.repo.list())


class ObtenerTipoEmpresa(BaseUseCase[TipoEmpresaRepo]):
    def execute(self, id: int) -> TipoEmpresaOut:
        tipo = self.repo.get(id)
        if not tipo:
            raise ValueError("tipo_empresa_no_encontrado")
        return tipo


class CrearTipoEmpresa(BaseUseCase[TipoEmpresaRepo]):
    def execute(self, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.create(data)


class ActualizarTipoEmpresa(BaseUseCase[TipoEmpresaRepo]):
    def execute(self, id: int, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.update(id, data)


class EliminarTipoEmpresa(BaseUseCase[TipoEmpresaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
