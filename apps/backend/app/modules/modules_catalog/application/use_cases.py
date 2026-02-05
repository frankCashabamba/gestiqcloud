from __future__ import annotations

from collections.abc import Sequence

from app.modules.modules_catalog.infrastructure.repositories import SqlModuloRepo
from app.modules.shared.application.base import BaseUseCase


class ListarModulosAdmin(BaseUseCase[SqlModuloRepo]):
    def execute(self) -> Sequence[dict]:
        return self.repo.list_all()


class ListarModulosAsignadosTenant(BaseUseCase[SqlModuloRepo]):
    def execute(self, *, tenant_user_id, tenant_id, is_admin: bool = False) -> Sequence[dict]:
        if is_admin:
            return self.repo.list_contracted(tenant_id=tenant_id)
        return self.repo.list_asignados(tenant_user_id=tenant_user_id, tenant_id=tenant_id)
