from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.clients.domain.entities import Cliente


class ClienteRepo(Protocol):
    def get(self, *, id: int, tenant_id: int) -> Cliente | None: ...

    def list(self, *, tenant_id: int, limit: int = 200, offset: int = 0, search: str | None = None) -> Sequence[Cliente]: ...

    def create(self, c: Cliente) -> Cliente: ...

    def update(self, c: Cliente) -> Cliente: ...

    def delete(self, *, id: int, tenant_id: int) -> None: ...
