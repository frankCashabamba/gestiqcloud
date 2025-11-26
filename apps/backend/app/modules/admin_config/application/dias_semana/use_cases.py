from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn, DiaSemanaOut
from app.modules.admin_config.application.dias_semana.ports import DiaSemanaRepo
from app.modules.shared.application.base import BaseUseCase


class ListWeekDays(BaseUseCase[DiaSemanaRepo]):
    def execute(self) -> Sequence[DiaSemanaOut]:
        return list(self.repo.list())


class GetWeekDay(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int) -> DiaSemanaOut:
        day = self.repo.get(id)
        if not day:
            raise ValueError("day_not_found")
        return day


class CreateWeekDay(BaseUseCase[DiaSemanaRepo]):
    def execute(self, data: DiaSemanaIn) -> DiaSemanaOut:
        return self.repo.create(data)


class UpdateWeekDay(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int, data: DiaSemanaIn) -> DiaSemanaOut:
        return self.repo.update(id, data)


class DeleteWeekDay(BaseUseCase[DiaSemanaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
