from __future__ import annotations

from typing import Optional, Sequence

from app.modules.productos.application.ports import ProductoRepo
from app.modules.productos.domain.entities import Producto
from app.modules.productos.infrastructure.models import ProductoORM
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo
from app.core.crud_base import CRUDBase


class ProductoCRUD(CRUDBase[ProductoORM, "ProductoCreateDTO", "ProductoUpdateDTO"]):
    pass


class SqlAlchemyProductoRepo(SqlAlchemyRepo, ProductoRepo):

    def _to_entity(self, m: ProductoORM) -> Producto:
        return Producto(id=m.id, nombre=m.nombre, precio=float(m.precio), activo=bool(m.activo), empresa_id=m.empresa_id)

    def get(self, id: int) -> Optional[Producto]:
        m = self.db.query(ProductoORM).filter(ProductoORM.id == id).first()
        return self._to_entity(m) if m else None

    def list(self, *, empresa_id: int) -> Sequence[Producto]:
        ms = (
            self.db.query(ProductoORM)
            .filter(ProductoORM.empresa_id == empresa_id)
            .order_by(ProductoORM.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in ms]

    def create(self, p: Producto) -> Producto:
        class ProductoCreateDTO:
            def __init__(self, **kw):
                self.nombre = kw.get("nombre")
                self.precio = kw.get("precio")
                self.activo = kw.get("activo")
                self.empresa_id = kw.get("empresa_id")

            def model_dump(self):
                return {
                    "nombre": self.nombre,
                    "precio": self.precio,
                    "activo": self.activo,
                    "empresa_id": self.empresa_id,
                }

        dto = ProductoCreateDTO(nombre=p.nombre, precio=p.precio, activo=p.activo, empresa_id=p.empresa_id)
        m = ProductoCRUD(ProductoORM).create(self.db, dto)
        return self._to_entity(m)

    def update(self, p: Producto) -> Producto:
        if p.id is None:
            raise ValueError("id requerido para update")

        class ProductoUpdateDTO:
            def __init__(self, **kw):
                self.nombre = kw.get("nombre")
                self.precio = kw.get("precio")
                self.activo = kw.get("activo")

            def model_dump(self, exclude_unset: bool = False):
                d = {"nombre": self.nombre, "precio": self.precio, "activo": self.activo}
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = ProductoUpdateDTO(nombre=p.nombre, precio=p.precio, activo=p.activo)
        m = ProductoCRUD(ProductoORM).update(self.db, p.id, dto)
        if not m:
            raise ValueError("producto no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ProductoCRUD(ProductoORM).delete(self.db, id)
        if not ok:
            return
