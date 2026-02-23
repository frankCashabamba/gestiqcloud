from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.core.global_catalogs import ExpenseCategoryGlobal as CategoriaGastoORM
from app.modules.admin_config.application.categorias_gasto.dto import CategoriaGastoIn, CategoriaGastoOut
from app.modules.admin_config.application.categorias_gasto.ports import CategoriaGastoRepo


class SqlAlchemyCategoriaGastoRepo(CategoriaGastoRepo):
    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, m: CategoriaGastoORM) -> CategoriaGastoOut:
        return CategoriaGastoOut(
            id=m.id,
            code=m.code,
            name=m.name,
            parent_code=m.parent_code,
            active=m.active,
        )

    def list(self) -> Sequence[CategoriaGastoOut]:
        rows = self.db.query(CategoriaGastoORM).order_by(CategoriaGastoORM.code.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: CategoriaGastoIn) -> CategoriaGastoOut:
        obj = CategoriaGastoORM(
            code=data.code,
            name=data.name,
            parent_code=data.parent_code,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: int) -> CategoriaGastoOut | None:
        obj = self.db.query(CategoriaGastoORM).filter(CategoriaGastoORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: int, data: CategoriaGastoIn) -> CategoriaGastoOut:
        obj = self.db.query(CategoriaGastoORM).filter(CategoriaGastoORM.id == id).first()
        if not obj:
            raise ValueError("expense_category_not_found")
        obj.code = data.code
        obj.name = data.name
        obj.parent_code = data.parent_code
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: int) -> None:
        obj = self.db.query(CategoriaGastoORM).filter(CategoriaGastoORM.id == id).first()
        if not obj:
            raise ValueError("expense_category_not_found")
        self.db.delete(obj)
        self.db.commit()
