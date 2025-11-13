"""Module: empresa.py

Auto-generated module docstring."""

from typing import List

from pydantic import BaseModel, ConfigDict

# Single source of truth for EmpresaCreate lives in `schemas.py`.
# Re-export here to keep public import path `app.schemas.empresa.EmpresaCreate` stable.
from app.schemas.schemas import EmpresaCreate  # noqa: F401


class EmpresaOut(BaseModel):
    """Class EmpresaOut - auto-generated docstring."""

    id: int
    name: str
    modulos: List[str] = []

    model_config = ConfigDict(from_attributes=True)  # Si us)
