from __future__ import annotations

from typing import Sequence

from app.modules.productos.application.dto import ProductoIn, ProductoOut
from app.modules.productos.application.ports import ProductoRepo
from app.modules.shared.application.base import BaseUseCase
from app.modules.productos.domain.entities import Producto


class CrearProducto(BaseUseCase[ProductoRepo]):

    def execute(self, *, empresa_id: int, data: ProductoIn) -> ProductoOut:
        p = Producto(id=None, nombre=data.nombre, precio=data.precio, activo=data.activo, empresa_id=empresa_id)
        p.validate()
        created = self.repo.create(p)
        return ProductoOut(id=created.id or 0, nombre=created.nombre, precio=created.precio, activo=created.activo)


class ListarProductos(BaseUseCase[ProductoRepo]):

    def execute(self, *, empresa_id: int) -> Sequence[ProductoOut]:
        items = self.repo.list(empresa_id=empresa_id)
        return [ProductoOut(id=i.id or 0, nombre=i.nombre, precio=i.precio, activo=i.activo) for i in items]
