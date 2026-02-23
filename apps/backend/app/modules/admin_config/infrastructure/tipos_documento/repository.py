from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.core.global_catalogs import DocumentType as TipoDocumentoORM
from app.modules.admin_config.application.tipos_documento.dto import TipoDocumentoIn, TipoDocumentoOut
from app.modules.admin_config.application.tipos_documento.ports import TipoDocumentoRepo


class SqlAlchemyTipoDocumentoRepo(TipoDocumentoRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: TipoDocumentoORM) -> TipoDocumentoOut:
        return TipoDocumentoOut(
            id=m.id,
            code=m.code,
            name=m.name,
            description=m.description,
            active=m.active,
        )

    def list(self) -> Sequence[TipoDocumentoOut]:
        rows = self.db.query(TipoDocumentoORM).order_by(TipoDocumentoORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TipoDocumentoIn) -> TipoDocumentoOut:
        obj = TipoDocumentoORM(
            code=data.code,
            name=data.name,
            description=data.description,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> TipoDocumentoOut | None:
        obj = self.db.query(TipoDocumentoORM).filter(TipoDocumentoORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: TipoDocumentoIn) -> TipoDocumentoOut:
        obj = self.db.query(TipoDocumentoORM).filter(TipoDocumentoORM.id == id).first()
        if not obj:
            raise ValueError("doc_type_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.description = data.description
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(TipoDocumentoORM).filter(TipoDocumentoORM.id == id).first()
        if not obj:
            raise ValueError("doc_type_not_found")
        self.db.delete(obj)
        self.db.commit()
