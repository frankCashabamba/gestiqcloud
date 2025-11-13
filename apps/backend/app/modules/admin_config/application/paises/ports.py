from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.paises.dto import PaisIn, PaisOut


class PaisRepo(Protocol):
    def list(self) -> Sequence[PaisOut]: ...

    def create(self, data: PaisIn) -> PaisOut: ...

    def get(self, id: int) -> Optional[PaisOut]: ...

    def update(self, id: int, data: PaisIn) -> PaisOut: ...

    def delete(self, id: int) -> None: ...
