from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.monedas.dto import MonedaIn, MonedaOut
from app.modules.admin_config.application.monedas.ports import MonedaRepo
from app.modules.shared.application.base import BaseUseCase


class ListarMonedas(BaseUseCase[MonedaRepo]):
    def execute(self) -> Sequence[MonedaOut]:
        return list(self.repo.list())


class ObtenerMoneda(BaseUseCase[MonedaRepo]):
    def execute(self, id: int) -> MonedaOut:
        moneda = self.repo.get(id)
        if not moneda:
            raise ValueError("moneda_no_encontrada")
        return moneda


class CrearMoneda(BaseUseCase[MonedaRepo]):
    def execute(self, data: MonedaIn) -> MonedaOut:
        return self.repo.create(data)


class ActualizarMoneda(BaseUseCase[MonedaRepo]):
    def execute(self, id: int, data: MonedaIn) -> MonedaOut:
        return self.repo.update(id, data)


class EliminarMoneda(BaseUseCase[MonedaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
