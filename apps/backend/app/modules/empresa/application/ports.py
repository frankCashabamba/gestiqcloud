from __future__ import annotations

from typing import Protocol, Sequence, Optional


class EmpresaDTO(dict):
    pass


class UsuarioEmpresaDTO(dict):
    pass


class EmpresaRepo(Protocol):
    def list_all(self) -> Sequence[EmpresaDTO]: ...

    def list_by_tenant(self, *, tenant_id: int) -> Sequence[EmpresaDTO]: ...

    def get(self, *, id: int) -> Optional[EmpresaDTO]: ...


class UsuarioEmpresaRepo(Protocol):
    def get_by_id(self, *, id: int) -> Optional[UsuarioEmpresaDTO]: ...
