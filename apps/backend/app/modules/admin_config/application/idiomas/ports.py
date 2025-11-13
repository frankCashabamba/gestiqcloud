from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut


class IdiomaRepo(Protocol):
    def list(self) -> Sequence[IdiomaOut]: ...

    def create(self, data: IdiomaIn) -> IdiomaOut: ...

    def get(self, id: int) -> Optional[IdiomaOut]: ...

    def update(self, id: int, data: IdiomaIn) -> IdiomaOut: ...

    def delete(self, id: int) -> None: ...
