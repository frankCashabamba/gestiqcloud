from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.metodos_pago_plantilla.dto import (
    MetodoPagoPlantillaIn,
    MetodoPagoPlantillaOut,
)
from app.modules.admin_config.application.metodos_pago_plantilla.ports import (
    MetodoPagoPlantillaRepo,
)
from app.modules.shared.application.base import BaseUseCase


class ListPaymentTemplates(BaseUseCase[MetodoPagoPlantillaRepo]):
    def execute(self) -> Sequence[MetodoPagoPlantillaOut]:
        return list(self.repo.list())


class GetPaymentTemplate(BaseUseCase[MetodoPagoPlantillaRepo]):
    def execute(self, id: int) -> MetodoPagoPlantillaOut:
        template = self.repo.get(id)
        if not template:
            raise ValueError("payment_template_not_found")
        return template


class CreatePaymentTemplate(BaseUseCase[MetodoPagoPlantillaRepo]):
    def execute(self, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut:
        return self.repo.create(data)


class UpdatePaymentTemplate(BaseUseCase[MetodoPagoPlantillaRepo]):
    def execute(self, id: int, data: MetodoPagoPlantillaIn) -> MetodoPagoPlantillaOut:
        return self.repo.update(id, data)


class DeletePaymentTemplate(BaseUseCase[MetodoPagoPlantillaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
