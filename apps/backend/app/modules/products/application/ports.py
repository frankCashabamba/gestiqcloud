from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.products.domain.entities import Producto


class ProductoRepo(Protocol):
    def get(self, id: int) -> Producto | None: ...

    def list(self, *, tenant_id: int) -> Sequence[Producto]: ...

    def create(self, p: Producto) -> Producto: ...

    def update(self, p: Producto) -> Producto: ...

    def delete(self, id: int) -> None: ...
