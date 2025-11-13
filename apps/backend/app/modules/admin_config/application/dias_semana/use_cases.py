from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn, DiaSemanaOut
from app.modules.admin_config.application.dias_semana.ports import DiaSemanaRepo
from app.modules.shared.application.base import BaseUseCase


class ListarDiasSemana(BaseUseCase[DiaSemanaRepo]):
    def execute(self) -> Sequence[DiaSemanaOut]:
        return list(self.repo.list())


class ObtenerDiaSemana(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int) -> DiaSemanaOut:
        dia = self.repo.get(id)
        if not dia:
            raise ValueError("dia_no_encontrado")
        return dia


class CrearDiaSemana(BaseUseCase[DiaSemanaRepo]):
    def execute(self, data: DiaSemanaIn) -> DiaSemanaOut:
        return self.repo.create(data)


class ActualizarDiaSemana(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int, data: DiaSemanaIn) -> DiaSemanaOut:
        return self.repo.update(id, data)


class EliminarDiaSemana(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
