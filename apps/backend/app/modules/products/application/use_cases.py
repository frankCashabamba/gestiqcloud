from __future__ import annotations

from collections.abc import Sequence

from app.modules.products.application.dto import ProductoIn, ProductoOut
from app.modules.products.application.ports import ProductoRepo
from app.modules.products.domain.entities import Producto
from app.modules.shared.application.base import BaseUseCase


class CrearProducto(BaseUseCase[ProductoRepo]):
    def execute(self, *, tenant_id: int, data: ProductoIn) -> ProductoOut:
        p = Producto(
            id=None,
            nombre=data.name,
            precio=data.price,
            activo=data.active,
            tenant_id=tenant_id,
        )
        p.validate()
        created = self.repo.create(p)
        return ProductoOut(
            id=created.id or 0,
            nombre=created.name,
            precio=created.price,
            activo=created.active,
        )


class ListarProductos(BaseUseCase[ProductoRepo]):
    def execute(self, *, tenant_id: int) -> Sequence[ProductoOut]:
        items = self.repo.list(tenant_id=tenant_id)
        return [
            ProductoOut(id=i.id or 0, nombre=i.name, precio=i.price, activo=i.active) for i in items
        ]
