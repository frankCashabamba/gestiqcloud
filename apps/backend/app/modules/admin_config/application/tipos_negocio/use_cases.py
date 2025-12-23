from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn, TipoNegocioOut
from app.modules.admin_config.application.tipos_negocio.ports import TipoNegocioRepo
from app.modules.shared.application.base import BaseUseCase


class ListBusinessTypes(BaseUseCase[TipoNegocioRepo]):
    def execute(self) -> Sequence[TipoNegocioOut]:
        return list(self.repo.list())


class GetBusinessType(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: UUID) -> TipoNegocioOut:
        business_type = self.repo.get(id)
        if not business_type:
            raise ValueError("business_type_not_found")
        return business_type


class CreateBusinessType(BaseUseCase[TipoNegocioRepo]):
    def execute(self, data: TipoNegocioIn) -> TipoNegocioOut:
        return self.repo.create(data)


class UpdateBusinessType(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: UUID, data: TipoNegocioIn) -> TipoNegocioOut:
        return self.repo.update(id, data)


class DeleteBusinessType(BaseUseCase[TipoNegocioRepo]):
    def execute(self, id: UUID) -> None:
        self.repo.delete(id)
