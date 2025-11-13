from __future__ import annotations

from typing import Protocol, Sequence, Optional

from app.modules.admin_config.application.horarios_atencion.dto import HorarioAtencionIn, HorarioAtencionOut


class HorarioAtencionRepo(Protocol):
    def list(self) -> Sequence[HorarioAtencionOut]: ...

    def create(self, data: HorarioAtencionIn) -> HorarioAtencionOut: ...

    def get(self, id: int) -> Optional[HorarioAtencionOut]: ...

    def update(self, id: int, data: HorarioAtencionIn) -> HorarioAtencionOut: ...

    def delete(self, id: int) -> None: ...
