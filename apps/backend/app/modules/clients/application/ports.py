from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.clients.domain.entities import Cliente


class ClienteRepo(Protocol):
    def get(self, id: int) -> Cliente | None: ...

    def list(self, *, tenant_id: int) -> Sequence[Cliente]: ...

    def create(self, c: Cliente) -> Cliente: ...

    def update(self, c: Cliente) -> Cliente: ...

    def delete(self, id: int) -> None: ...
