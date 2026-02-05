from __future__ import annotations

from collections.abc import Sequence

from app.models.core.module import AssignedModule, CompanyModule, Module
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


class SqlModuloRepo(SqlAlchemyRepo):
    def list_all(self) -> Sequence[dict]:
        rows = self.db.query(Module).filter(Module.active).order_by(Module.id.asc()).all()  # noqa: E712
        return [self._to_dto(m) for m in rows]

    def list_asignados(self, *, tenant_user_id, tenant_id) -> Sequence[dict]:
        rows = (
            self.db.query(AssignedModule)
            .filter(
                AssignedModule.user_id == tenant_user_id,
                AssignedModule.tenant_id == tenant_id,
            )
            .all()
        )
        return [self._to_dto(ma.module) for ma in rows if ma.module]

    def list_contracted(self, *, tenant_id) -> Sequence[dict]:
        rows = (
            self.db.query(CompanyModule)
            .filter(
                CompanyModule.tenant_id == tenant_id,
                CompanyModule.active,  # noqa: E712
            )
            .all()
        )
        return [self._to_dto(cm.module) for cm in rows if cm.module]

    def _to_dto(self, m: Module) -> dict:
        return {
            "id": m.id,
            "name": m.name,
            "url": m.url,
            "icon": m.icon,
            "category": m.category,
            "active": m.active,
        }
