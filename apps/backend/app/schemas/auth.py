"""Module: auth.py

Auto-generated module docstring."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """ Class LoginRequest - auto-generated docstring. """
    email: str
    password: str

class TokenResponse(BaseModel):
    """ Class TokenResponse - auto-generated docstring. """
    access_token: str
    token_type: str = "bearer"
