from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.paises.dto import PaisIn, PaisOut
from app.modules.admin_config.application.paises.ports import PaisRepo
from app.modules.shared.application.base import BaseUseCase


class ListarPaises(BaseUseCase[PaisRepo]):
    def execute(self) -> Sequence[PaisOut]:
        return list(self.repo.list())


class ObtenerPais(BaseUseCase[PaisRepo]):
    def execute(self, id: int) -> PaisOut:
        pais = self.repo.get(id)
        if not pais:
            raise ValueError("pais_no_encontrado")
        return pais


class CrearPais(BaseUseCase[PaisRepo]):
    def execute(self, data: PaisIn) -> PaisOut:
        return self.repo.create(data)


class ActualizarPais(BaseUseCase[PaisRepo]):
    def execute(self, id: int, data: PaisIn) -> PaisOut:
        return self.repo.update(id, data)


class EliminarPais(BaseUseCase[PaisRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
