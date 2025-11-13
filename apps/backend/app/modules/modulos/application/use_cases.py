from __future__ import annotations

from typing import Sequence

from app.modules.modulos.infrastructure.repositories import SqlModuloRepo
from app.modules.shared.application.base import BaseUseCase


class ListarModulosAdmin(BaseUseCase[SqlModuloRepo]):
    def execute(self) -> Sequence[dict]:
        return self.repo.list_all()


class ListarModulosAsignadosTenant(BaseUseCase[SqlModuloRepo]):
    def execute(self, *, tenant_user_id, tenant_id) -> Sequence[dict]:
        return self.repo.list_asignados(
            tenant_user_id=tenant_user_id, tenant_id=tenant_id
        )
