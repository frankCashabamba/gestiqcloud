from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.timezones.dto import TimezoneIn, TimezoneOut
from app.modules.admin_config.application.timezones.ports import TimezoneRepo
from app.modules.shared.application.base import BaseUseCase


class ListarTimezones(BaseUseCase[TimezoneRepo]):
    def execute(self) -> Sequence[TimezoneOut]:
        return list(self.repo.list())


class ObtenerTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str) -> TimezoneOut:
        tz = self.repo.get(name)
        if not tz:
            raise ValueError("timezone_no_encontrado")
        return tz


class CrearTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, data: TimezoneIn) -> TimezoneOut:
        return self.repo.create(data)


class ActualizarTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str, data: TimezoneIn) -> TimezoneOut:
        return self.repo.update(name, data)


class EliminarTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str) -> None:
        self.repo.delete(name)
