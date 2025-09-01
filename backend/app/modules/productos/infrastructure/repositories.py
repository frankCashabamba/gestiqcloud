from __future__ import annotations

from typing import Optional, Sequence

from app.modules.productos.application.ports import ProductoRepo
from app.modules.productos.domain.entities import Producto
from app.modules.productos.infrastructure.models import ProductoORM
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


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
        m = ProductoORM(nombre=p.nombre, precio=p.precio, activo=p.activo, empresa_id=p.empresa_id)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_entity(m)

    def update(self, p: Producto) -> Producto:
        if p.id is None:
            raise ValueError("id requerido para update")
        m = self.db.query(ProductoORM).filter(ProductoORM.id == p.id).first()
        if not m:
            raise ValueError("producto no existe")
        m.nombre = p.nombre
        m.precio = p.precio
        m.activo = p.activo
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        m = self.db.query(ProductoORM).filter(ProductoORM.id == id).first()
        if not m:
            return
        self.db.delete(m)
        self.db.commit()
