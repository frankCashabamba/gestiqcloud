from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.tipos_impuesto.dto import (
    TipoImpuestoIn,
    TipoImpuestoOut,
)
from app.modules.admin_config.application.tipos_impuesto.ports import TipoImpuestoRepo
from app.modules.shared.application.base import BaseUseCase


class ListTaxTypes(BaseUseCase[TipoImpuestoRepo]):
    def execute(self) -> Sequence[TipoImpuestoOut]:
        return list(self.repo.list())


class GetTaxType(BaseUseCase[TipoImpuestoRepo]):
    def execute(self, id: str) -> TipoImpuestoOut:
        tax_type = self.repo.get(id)
        if not tax_type:
            raise ValueError("tax_type_not_found")
        return tax_type


class CreateTaxType(BaseUseCase[TipoImpuestoRepo]):
    def execute(self, data: TipoImpuestoIn) -> TipoImpuestoOut:
        return self.repo.create(data)


class UpdateTaxType(BaseUseCase[TipoImpuestoRepo]):
    def execute(self, id: str, data: TipoImpuestoIn) -> TipoImpuestoOut:
        return self.repo.update(id, data)


class DeleteTaxType(BaseUseCase[TipoImpuestoRepo]):
    def execute(self, id: str) -> None:
        self.repo.delete(id)
