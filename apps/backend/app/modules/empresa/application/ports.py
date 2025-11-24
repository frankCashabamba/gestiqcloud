from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class CompanyDTO(dict):
    pass


class CompanyUserDTO(dict):
    pass


class CompanyRepo(Protocol):
    def list_all(self) -> Sequence[CompanyDTO]: ...

    def list_by_tenant(self, *, tenant_id: int) -> Sequence[CompanyDTO]: ...

    def get(self, *, id: int) -> CompanyDTO | None: ...


class CompanyUserRepo(Protocol):
    def get_by_id(self, *, id: int) -> CompanyUserDTO | None: ...
