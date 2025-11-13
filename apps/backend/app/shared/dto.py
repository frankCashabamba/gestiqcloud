from typing import Generic, Optional, Sequence, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


class IDModel(BaseDTO):
    id: int


class Timestamped(BaseDTO):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Page(Generic[T], BaseModel):
    items: Sequence[T]
    total: int
    limit: int
    offset: int
