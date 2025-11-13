from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.timezones.dto import TimezoneIn, TimezoneOut


class TimezoneRepo(Protocol):
    def list(self) -> Sequence[TimezoneOut]: ...

    def create(self, data: TimezoneIn) -> TimezoneOut: ...

    def get(self, name: str) -> Optional[TimezoneOut]: ...

    def update(self, name: str, data: TimezoneIn) -> TimezoneOut: ...

    def delete(self, name: str) -> None: ...
