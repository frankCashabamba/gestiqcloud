from __future__ import annotations

from typing import Sequence

from app.modules.admin_config.application.horarios_atencion.dto import HorarioAtencionIn, HorarioAtencionOut
from app.modules.admin_config.application.horarios_atencion.ports import HorarioAtencionRepo
from app.modules.shared.application.base import BaseUseCase


class ListarHorariosAtencion(BaseUseCase[HorarioAtencionRepo]):
    def execute(self) -> Sequence[HorarioAtencionOut]:
        return list(self.repo.list())


class ObtenerHorarioAtencion(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int) -> HorarioAtencionOut:
        horario = self.repo.get(id)
        if not horario:
            raise ValueError("horario_no_encontrado")
        return horario


class CrearHorarioAtencion(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, data: HorarioAtencionIn) -> HorarioAtencionOut:
        return self.repo.create(data)


class ActualizarHorarioAtencion(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int, data: HorarioAtencionIn) -> HorarioAtencionOut:
        return self.repo.update(id, data)


class EliminarHorarioAtencion(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
