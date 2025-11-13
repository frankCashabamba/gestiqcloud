from __future__ import annotations

from collections.abc import Sequence

from app.core.crud_base import CRUDBase
from app.models.core.products import Product  # ✅ CORREGIDO: modelo centralizado
from app.modules.productos.application.ports import ProductoRepo
from app.modules.productos.domain.entities import Producto
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


class ProductoCRUD(CRUDBase[Product, "ProductoCreateDTO", "ProductoUpdateDTO"]):
    pass


class SqlAlchemyProductoRepo(SqlAlchemyRepo, ProductoRepo):
    def _to_entity(self, m: Product) -> Producto:
        return Producto(
            id=m.id,
            nombre=m.name,
            precio=float(m.price),
            activo=bool(m.active),
            tenant_id=m.tenant_id,
        )

    def get(self, id: int) -> Producto | None:
        m = self.db.query(Product).filter(Product.id == id).first()
        return self._to_entity(m) if m else None

    def list(self, *, tenant_id: int) -> Sequence[Producto]:
        ms = (
            self.db.query(Product)
            .filter(Product.tenant_id == tenant_id)
            .order_by(Product.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in ms]

    def create(self, p: Producto) -> Producto:
        class ProductoCreateDTO:
            def __init__(self, **kw):
                self.name = kw.get("nombre")
                self.price = kw.get("precio")
                self.active = kw.get("activo")
                self.tenant_id = kw.get("tenant_id")

            def model_dump(self):
                return {
                    "nombre": self.name,
                    "precio": self.price,
                    "activo": self.active,
                    "tenant_id": self.tenant_id,
                }

        dto = ProductoCreateDTO(
            nombre=p.name, precio=p.price, activo=p.active, tenant_id=p.tenant_id
        )
        m = ProductoCRUD(Product).create(self.db, dto)
        return self._to_entity(m)

    def update(self, p: Producto) -> Producto:
        if p.id is None:
            raise ValueError("id requerido para update")

        class ProductoUpdateDTO:
            def __init__(self, **kw):
                self.name = kw.get("nombre")
                self.price = kw.get("precio")
                self.active = kw.get("activo")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "nombre": self.name,
                    "precio": self.price,
                    "activo": self.active,
                }
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = ProductoUpdateDTO(nombre=p.name, precio=p.price, activo=p.active)
        m = ProductoCRUD(Product).update(self.db, p.id, dto)
        if not m:
            raise ValueError("producto no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ProductoCRUD(Product).delete(self.db, id)
        if not ok:
            return
