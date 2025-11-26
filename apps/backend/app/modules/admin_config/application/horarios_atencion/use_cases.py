from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.horarios_atencion.dto import (
    HorarioAtencionIn,
    HorarioAtencionOut,
)
from app.modules.admin_config.application.horarios_atencion.ports import HorarioAtencionRepo
from app.modules.shared.application.base import BaseUseCase


class ListAttentionSchedules(BaseUseCase[HorarioAtencionRepo]):
    def execute(self) -> Sequence[HorarioAtencionOut]:
        return list(self.repo.list())


class GetAttentionSchedule(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int) -> HorarioAtencionOut:
        schedule = self.repo.get(id)
        if not schedule:
            raise ValueError("schedule_not_found")
        return schedule


class CreateAttentionSchedule(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, data: HorarioAtencionIn) -> HorarioAtencionOut:
        return self.repo.create(data)


class UpdateAttentionSchedule(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int, data: HorarioAtencionIn) -> HorarioAtencionOut:
        return self.repo.update(id, data)


class DeleteAttentionSchedule(BaseUseCase[HorarioAtencionRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
