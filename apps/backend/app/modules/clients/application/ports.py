from __future__ import annotations

from typing import Protocol, Optional, Sequence

from app.modules.clients.domain.entities import Cliente


class ClienteRepo(Protocol):
    def get(self, id: int) -> Optional[Cliente]:
        ...

    def list(self, *, empresa_id: int) -> Sequence[Cliente]:
        ...

    def create(self, c: Cliente) -> Cliente:
        ...

    def update(self, c: Cliente) -> Cliente:
        ...

    def delete(self, id: int) -> None:
        ...

