from __future__ import annotations

from typing import Sequence

from app.modules.admin_config.application.locales.dto import LocaleIn, LocaleOut
from app.modules.admin_config.application.locales.ports import LocaleRepo
from app.modules.shared.application.base import BaseUseCase


class ListarLocales(BaseUseCase[LocaleRepo]):
    def execute(self) -> Sequence[LocaleOut]:
        return list(self.repo.list())


class ObtenerLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str) -> LocaleOut:
        locale = self.repo.get(code)
        if not locale:
            raise ValueError("locale_no_encontrado")
        return locale


class CrearLocale(BaseUseCase[LocaleRepo]):
    def execute(self, data: LocaleIn) -> LocaleOut:
        return self.repo.create(data)


class ActualizarLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str, data: LocaleIn) -> LocaleOut:
        return self.repo.update(code, data)


class EliminarLocale(BaseUseCase[LocaleRepo]):
    def execute(self, code: str) -> None:
        self.repo.delete(code)
