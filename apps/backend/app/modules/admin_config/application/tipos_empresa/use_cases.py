from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut
from app.modules.admin_config.application.tipos_empresa.ports import TipoCompanyRepo
from app.modules.shared.application.base import BaseUseCase


class ListCompanyTypes(BaseUseCase[TipoCompanyRepo]):
    def execute(self) -> Sequence[TipoEmpresaOut]:
        return list(self.repo.list())


class GetCompanyType(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str) -> TipoEmpresaOut:
        company_type = self.repo.get(id)
        if not company_type:
            raise ValueError("company_type_not_found")
        return company_type


class CreateCompanyType(BaseUseCase[TipoCompanyRepo]):
    def execute(self, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.create(data)


class UpdateCompanyType(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str, data: TipoEmpresaIn) -> TipoEmpresaOut:
        return self.repo.update(id, data)


class DeleteCompanyType(BaseUseCase[TipoCompanyRepo]):
    def execute(self, id: UUID | str) -> None:
        self.repo.delete(id)
