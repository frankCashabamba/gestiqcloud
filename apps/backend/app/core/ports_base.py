from __future__ import annotations

from typing import Generic, Optional, Protocol, Sequence, TypeVar

T = TypeVar("T")


class ReadPort(Protocol[T]):
    def get(self, id: int) -> Optional[T]:
        ...

    def list(self, *args, **kwargs) -> Sequence[T]:
        ...


class WritePort(Protocol[T]):
    def create(self, obj: T) -> T:  # or DTO depending on module
        ...

    def update(self, obj: T) -> T:
        ...

    def delete(self, id: int) -> None | bool:
        ...


class CRUDPort(ReadPort[T], WritePort[T], Generic[T], Protocol):
    """Base CRUD port to document common signatures across modules.

    Nota: No obliga cambios en puertos existentes; sirve como referencia
    para reducir duplicación en nuevos módulos.
    """
    ...

