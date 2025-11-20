from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut


class IdiomaRepo(Protocol):
    def list(self) -> Sequence[IdiomaOut]: ...

    def create(self, data: IdiomaIn) -> IdiomaOut: ...

    def get(self, id: int) -> IdiomaOut | None: ...

    def update(self, id: int, data: IdiomaIn) -> IdiomaOut: ...

    def delete(self, id: int) -> None: ...
