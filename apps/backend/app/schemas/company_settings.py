"""Module: company_settings.py

Auto-generated module docstring."""

from pydantic import BaseModel, ConfigDict

from app.settings.schemas.company_settings import (  # noqa: F401
    CompanySettingsCreate as CompanySettingsCreate,
)


class CompanySettingsOut(BaseModel):
    """Class CompanySettingsOut - auto-generated docstring."""

    company_logo: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    company_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
