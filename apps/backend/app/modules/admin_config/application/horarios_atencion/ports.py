from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin_config.application.horarios_atencion.dto import (
    HorarioAtencionIn,
    HorarioAtencionOut,
)


class HorarioAtencionRepo(Protocol):
    def list(self) -> Sequence[HorarioAtencionOut]: ...

    def create(self, data: HorarioAtencionIn) -> HorarioAtencionOut: ...

    def get(self, id: int) -> HorarioAtencionOut | None: ...

    def update(self, id: int, data: HorarioAtencionIn) -> HorarioAtencionOut: ...

    def delete(self, id: int) -> None: ...
