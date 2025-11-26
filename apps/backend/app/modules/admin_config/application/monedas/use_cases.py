from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.monedas.dto import MonedaIn, MonedaOut
from app.modules.admin_config.application.monedas.ports import MonedaRepo
from app.modules.shared.application.base import BaseUseCase


class ListCurrencies(BaseUseCase[MonedaRepo]):
    def execute(self) -> Sequence[MonedaOut]:
        return list(self.repo.list())


class GetCurrency(BaseUseCase[MonedaRepo]):
    def execute(self, id: int) -> MonedaOut:
        currency = self.repo.get(id)
        if not currency:
            raise ValueError("currency_not_found")
        return currency


class CreateCurrency(BaseUseCase[MonedaRepo]):
    def execute(self, data: MonedaIn) -> MonedaOut:
        return self.repo.create(data)


class UpdateCurrency(BaseUseCase[MonedaRepo]):
    def execute(self, id: int, data: MonedaIn) -> MonedaOut:
        return self.repo.update(id, data)


class DeleteCurrency(BaseUseCase[MonedaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
