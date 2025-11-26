"""Module: company.py

Auto-generated module docstring."""

# Single source of truth for CompanyCreate lives in `schemas.py`.
# Re-export here to keep public import path `app.schemas.company.CompanyCreate` stable.
from pydantic import BaseModel, ConfigDict

from app.schemas.schemas import EmpresaCreate as CompanyCreate  # noqa: F401


class CompanyOut(BaseModel):
    """Class CompanyOut - auto-generated docstring."""

    id: int
    name: str
    modulos: list[str] = []

    model_config = ConfigDict(from_attributes=True)
