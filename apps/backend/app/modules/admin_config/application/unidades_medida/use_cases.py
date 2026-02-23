from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.unidades_medida.dto import (
    UnidadMedidaIn,
    UnidadMedidaOut,
)
from app.modules.admin_config.application.unidades_medida.ports import UnidadMedidaRepo
from app.modules.shared.application.base import BaseUseCase


class ListUnits(BaseUseCase[UnidadMedidaRepo]):
    def execute(self) -> Sequence[UnidadMedidaOut]:
        return list(self.repo.list())


class GetUnit(BaseUseCase[UnidadMedidaRepo]):
    def execute(self, id: int) -> UnidadMedidaOut:
        unit = self.repo.get(id)
        if not unit:
            raise ValueError("unit_not_found")
        return unit


class CreateUnit(BaseUseCase[UnidadMedidaRepo]):
    def execute(self, data: UnidadMedidaIn) -> UnidadMedidaOut:
        return self.repo.create(data)


class UpdateUnit(BaseUseCase[UnidadMedidaRepo]):
    def execute(self, id: int, data: UnidadMedidaIn) -> UnidadMedidaOut:
        return self.repo.update(id, data)


class DeleteUnit(BaseUseCase[UnidadMedidaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
