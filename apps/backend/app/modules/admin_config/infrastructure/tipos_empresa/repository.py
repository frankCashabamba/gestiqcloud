from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.empresa.empresa import TipoEmpresa as TipoEmpresaORM
from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut
from app.modules.admin_config.application.tipos_empresa.ports import TipoEmpresaRepo


class SqlAlchemyTipoEmpresaRepo(TipoEmpresaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, t: TipoEmpresaORM) -> TipoEmpresaOut:
        return TipoEmpresaOut(
            id=t.id,
            name=t.name,
            description=t.description,
            active=t.active,
        )

    def list(self) -> Sequence[TipoEmpresaOut]:
        rows = self.db.query(TipoEmpresaORM).order_by(TipoEmpresaORM.name.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TipoEmpresaIn) -> TipoEmpresaOut:
        obj = TipoEmpresaORM(
            name=data.name,
            description=data.description,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> TipoEmpresaOut | None:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: TipoEmpresaIn) -> TipoEmpresaOut:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        if not obj:
            raise ValueError("tipo_empresa_no_encontrado")
        obj.name = data.name
        obj.description = data.description
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        if not obj:
            raise ValueError("tipo_empresa_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
