from __future__ import annotations

from typing import Sequence

from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn, TipoNegocioOut
from app.modules.admin_config.application.tipos_negocio.ports import TipoNegocioRepo
from app.modules.shared.application.base import BaseUseCase


class ListarTiposNegocio(BaseUseCase[TipoNegocioRepo]):
    def execute(self) -> Sequence[TipoNegocioOut]:
        return list(self.repo.list())


class ObtenerTipoNegocio(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: int) -> TipoNegocioOut:
        tipo = self.repo.get(id)
        if not tipo:
            raise ValueError("tipo_negocio_no_encontrado")
        return tipo


class CrearTipoNegocio(BaseUseCase[TipoNegocioRepo]):
    def execute(self, data: TipoNegocioIn) -> TipoNegocioOut:
        return self.repo.create(data)


class ActualizarTipoNegocio(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: int, data: TipoNegocioIn) -> TipoNegocioOut:
        return self.repo.update(id, data)


class EliminarTipoNegocio(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
