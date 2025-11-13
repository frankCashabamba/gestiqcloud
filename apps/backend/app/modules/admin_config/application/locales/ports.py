from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.locales.dto import LocaleIn, LocaleOut


class LocaleRepo(Protocol):
    def list(self) -> Sequence[LocaleOut]: ...

    def create(self, data: LocaleIn) -> LocaleOut: ...

    def get(self, code: str) -> LocaleOut | None: ...

    def update(self, code: str, data: LocaleIn) -> LocaleOut: ...

    def delete(self, code: str) -> None: ...
