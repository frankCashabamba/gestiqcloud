from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.locales.dto import LocaleIn, LocaleOut
from app.modules.admin_config.application.locales.ports import LocaleRepo
from app.modules.shared.application.base import BaseUseCase


class ListLocales(BaseUseCase[LocaleRepo]):
    def execute(self) -> Sequence[LocaleOut]:
        return list(self.repo.list())


class GetLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str) -> LocaleOut:
        locale = self.repo.get(code)
        if not locale:
            raise ValueError("locale_not_found")
        return locale


class CreateLocale(BaseUseCase[LocaleRepo]):
    def execute(self, data: LocaleIn) -> LocaleOut:
        return self.repo.create(data)


class UpdateLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str, data: LocaleIn) -> LocaleOut:
        return self.repo.update(code, data)


class DeleteLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str) -> None:
        self.repo.delete(code)
