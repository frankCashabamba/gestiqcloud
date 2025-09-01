from __future__ import annotations

from typing import Sequence

from app.modules.empresa.application.ports import EmpresaRepo, EmpresaDTO
from app.modules.shared.application.base import BaseUseCase


class ListarEmpresasAdmin(BaseUseCase[EmpresaRepo]):

    def execute(self) -> Sequence[EmpresaDTO]:
        return list(self.repo.list_all())


class ListarEmpresasTenant(BaseUseCase[EmpresaRepo]):

    def execute(self, *, tenant_id: int) -> Sequence[EmpresaDTO]:
        return list(self.repo.list_by_tenant(tenant_id=tenant_id))
