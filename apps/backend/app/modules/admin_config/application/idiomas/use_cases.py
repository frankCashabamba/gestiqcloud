from __future__ import annotations

from typing import Sequence

from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut
from app.modules.admin_config.application.idiomas.ports import IdiomaRepo
from app.modules.shared.application.base import BaseUseCase


class ListarIdiomas(BaseUseCase[IdiomaRepo]):
    def execute(self) -> Sequence[IdiomaOut]:
        return list(self.repo.list())


class ObtenerIdioma(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int) -> IdiomaOut:
        idioma = self.repo.get(id)
        if not idioma:
            raise ValueError("idioma_no_encontrado")
        return idioma


class CrearIdioma(BaseUseCase[IdiomaRepo]):
    def execute(self, data: IdiomaIn) -> IdiomaOut:
        return self.repo.create(data)


class ActualizarIdioma(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int, data: IdiomaIn) -> IdiomaOut:
        return self.repo.update(id, data)


class EliminarIdioma(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
