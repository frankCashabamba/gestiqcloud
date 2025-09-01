from __future__ import annotations

from typing import Sequence

from app.models.core.modulo import Modulo, ModuloAsignado
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


class SqlModuloRepo(SqlAlchemyRepo):

    def list_all(self) -> Sequence[dict]:
        rows = self.db.query(Modulo).filter(Modulo.activo == True).order_by(Modulo.id.asc()).all()  # noqa: E712
        return [self._to_dto(m) for m in rows]

    def list_asignados(self, *, tenant_user_id: int, tenant_id: int) -> Sequence[dict]:
        rows = (
            self.db.query(ModuloAsignado)
            .filter(
                ModuloAsignado.usuario_id == tenant_user_id,
                ModuloAsignado.empresa_id == tenant_id,
                ModuloAsignado.ver_modulo_auto == True,  # noqa: E712
            )
            .all()
        )
        return [self._to_dto(ma.modulo) for ma in rows if ma.modulo]

    def _to_dto(self, m: Modulo) -> dict:
        return dict(id=m.id, nombre=m.nombre, url=m.url, icono=m.icono, categoria=m.categoria, activo=m.activo)
