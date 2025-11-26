from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.timezones.dto import TimezoneIn, TimezoneOut
from app.modules.admin_config.application.timezones.ports import TimezoneRepo
from app.modules.shared.application.base import BaseUseCase


class ListTimezones(BaseUseCase[TimezoneRepo]):
    def execute(self) -> Sequence[TimezoneOut]:
        return list(self.repo.list())


class GetTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str) -> TimezoneOut:
        timezone = self.repo.get(name)
        if not timezone:
            raise ValueError("timezone_not_found")
        return timezone


class CreateTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, data: TimezoneIn) -> TimezoneOut:
        return self.repo.create(data)


class UpdateTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str, data: TimezoneIn) -> TimezoneOut:
        return self.repo.update(name, data)


class DeleteTimezone(BaseUseCase[TimezoneRepo]):
    def execute(self, name: str) -> None:
        self.repo.delete(name)
