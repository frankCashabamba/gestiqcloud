from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.locales.dto import LocaleIn, LocaleOut


class LocaleRepo(Protocol):
    def list(self) -> Sequence[LocaleOut]: ...

    def create(self, data: LocaleIn) -> LocaleOut: ...

    def get(self, code: str) -> Optional[LocaleOut]: ...

    def update(self, code: str, data: LocaleIn) -> LocaleOut: ...

    def delete(self, code: str) -> None: ...
