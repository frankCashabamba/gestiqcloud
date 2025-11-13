from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class EmpresaDTO(dict):
    pass


class UsuarioEmpresaDTO(dict):
    pass


class EmpresaRepo(Protocol):
    def list_all(self) -> Sequence[EmpresaDTO]: ...

    def list_by_tenant(self, *, tenant_id: int) -> Sequence[EmpresaDTO]: ...

    def get(self, *, id: int) -> EmpresaDTO | None: ...


class UsuarioEmpresaRepo(Protocol):
    def get_by_id(self, *, id: int) -> UsuarioEmpresaDTO | None: ...
