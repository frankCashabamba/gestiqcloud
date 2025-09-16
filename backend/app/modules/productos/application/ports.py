from __future__ import annotations

from typing import Protocol, Optional, Sequence

from app.modules.productos.domain.entities import Producto


class ProductoRepo(Protocol):
    def get(self, id: int) -> Optional[Producto]:
        ...

    def list(self, *, empresa_id: int) -> Sequence[Producto]:
        ...

    def create(self, p: Producto) -> Producto:
        ...

    def update(self, p: Producto) -> Producto:
        ...

    def delete(self, id: int) -> None:
        ...

