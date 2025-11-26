from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.crud_base import CRUDBase
from app.models.core.products import Product  # ✅ CORREGIDO: modelo centralizado
from app.modules.products.application.ports import ProductoRepo
from app.modules.products.domain.entities import Producto
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


@dataclass
class ProductoCreateDTO:
    nombre: str
    precio: float
    activo: bool = True
    tenant_id: int | None = None

    def model_dump(self) -> dict:
        return {
            "nombre": self.nombre,
            "precio": self.precio,
            "activo": self.activo,
            "tenant_id": self.tenant_id,
        }


@dataclass
class ProductoUpdateDTO:
    nombre: str | None = None
    precio: float | None = None
    activo: bool | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "nombre": self.nombre,
            "precio": self.precio,
            "activo": self.activo,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class ProductoCRUD(CRUDBase[Product, ProductoCreateDTO, ProductoUpdateDTO]):
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
        dto = ProductoCreateDTO(
            nombre=p.name, precio=p.price, activo=p.active, tenant_id=p.tenant_id
        )
        m = ProductoCRUD(Product).create(self.db, dto)
        return self._to_entity(m)

    def update(self, p: Producto) -> Producto:
        if p.id is None:
            raise ValueError("id requerido para update")

        dto = ProductoUpdateDTO(nombre=p.name, precio=p.price, activo=p.active)
        m = ProductoCRUD(Product).update(self.db, p.id, dto)
        if not m:
            raise ValueError("producto no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ProductoCRUD(Product).delete(self.db, id)
        if not ok:
            return
