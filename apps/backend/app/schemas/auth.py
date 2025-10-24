"""Module: auth.py

Auto-generated module docstring."""

from pydantic import BaseModel
from uuid import UUID, uuid4


class LoginRequest(BaseModel):
    """ Class LoginRequest - auto-generated docstring. """
    email: str
    password: str

class TokenResponse(BaseModel):
    """ Class TokenResponse - auto-generated docstring. """
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    """Minimal user schema used for dependency typing in routers.

    Only fields that are required by routers/tests are included.
    """
    id: UUID | None = None
    tenant_id: UUID
