from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


class IDModel(BaseDTO):
    id: int


class Timestamped(BaseDTO):
    created_at: str | None = None
    updated_at: str | None = None


class Page(Generic[T], BaseModel):
    items: Sequence[T]
    total: int
    limit: int
    offset: int
