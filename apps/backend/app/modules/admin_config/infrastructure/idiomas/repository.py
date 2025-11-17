from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.empresa.empresa import Idioma as IdiomaORM
from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut
from app.modules.admin_config.application.idiomas.ports import IdiomaRepo


class SqlAlchemyIdiomaRepo(IdiomaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, i: IdiomaORM) -> IdiomaOut:
        return IdiomaOut(
            id=i.id,
            codigo=i.codigo,
            nombre=i.nombre,
            active=i.activo,
        )

    def list(self) -> Sequence[IdiomaOut]:
        rows = self.db.query(IdiomaORM).order_by(IdiomaORM.codigo.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: IdiomaIn) -> IdiomaOut:
        obj = IdiomaORM(
            codigo=data.codigo,
            nombre=data.nombre,
            activo=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> IdiomaOut | None:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: IdiomaIn) -> IdiomaOut:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        if not obj:
            raise ValueError("idioma_no_encontrado")
        obj.codigo = data.codigo
        obj.nombre = data.nombre
        obj.activo = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(IdiomaORM).filter(IdiomaORM.id == id).first()
        if not obj:
            raise ValueError("idioma_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
