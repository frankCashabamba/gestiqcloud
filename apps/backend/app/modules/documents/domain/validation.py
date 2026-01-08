from __future__ import annotations

from pydantic import BaseModel


class ValidationError(BaseModel):
    code: str
    message: str
    field: str | None = None
