from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.monedas.dto import MonedaIn, MonedaOut


class MonedaRepo(Protocol):
    def list(self) -> Sequence[MonedaOut]: ...

    def create(self, data: MonedaIn) -> MonedaOut: ...

    def get(self, id: int) -> Optional[MonedaOut]: ...

    def update(self, id: int, data: MonedaIn) -> MonedaOut: ...

    def delete(self, id: int) -> None: ...
