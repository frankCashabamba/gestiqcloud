from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn, DiaSemanaOut


class DiaSemanaRepo(Protocol):
    def list(self) -> Sequence[DiaSemanaOut]: ...

    def create(self, data: DiaSemanaIn) -> DiaSemanaOut: ...

    def get(self, id: int) -> DiaSemanaOut | None: ...

    def update(self, id: int, data: DiaSemanaIn) -> DiaSemanaOut: ...

    def delete(self, id: int) -> None: ...
