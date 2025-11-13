from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.paises.dto import PaisIn, PaisOut


class PaisRepo(Protocol):
    def list(self) -> Sequence[PaisOut]: ...

    def create(self, data: PaisIn) -> PaisOut: ...

    def get(self, id: int) -> PaisOut | None: ...

    def update(self, id: int, data: PaisIn) -> PaisOut: ...

    def delete(self, id: int) -> None: ...
