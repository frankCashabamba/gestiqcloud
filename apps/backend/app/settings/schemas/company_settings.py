"""Module: company_settings.py

Auto-generated module docstring."""

from pydantic import BaseModel, ConfigDict


class CompanySettingsBase(BaseModel):
    """Class CompanySettingsBase - auto-generated docstring."""

    default_language: str | None = None
    timezone: str | None = None
    currency: str | None = None
    company_logo: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None


class CompanySettingsCreate(CompanySettingsBase):
    """Class CompanySettingsCreate - auto-generated docstring."""

    tenant_id: int
    primary_color: str
    secondary_color: str
    default_language: str
    timezone: str
    currency: str


class CompanySettingsUpdate(CompanySettingsBase):
    """Class CompanySettingsUpdate - auto-generated docstring."""

    pass


class CompanySettingsOut(CompanySettingsBase):
    """Class CompanySettingsOut - auto-generated docstring."""

    id: int
    tenant_id: int
    primary_color: str
    secondary_color: str

    model_config = ConfigDict(from_attributes=True)
