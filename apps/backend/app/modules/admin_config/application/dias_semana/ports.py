from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn, DiaSemanaOut


class DiaSemanaRepo(Protocol):
    def list(self) -> Sequence[DiaSemanaOut]: ...

    def create(self, data: DiaSemanaIn) -> DiaSemanaOut: ...

    def get(self, id: int) -> Optional[DiaSemanaOut]: ...

    def update(self, id: int, data: DiaSemanaIn) -> DiaSemanaOut: ...

    def delete(self, id: int) -> None: ...
