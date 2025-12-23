"""Compatibility layer for legacy TenantSettings model.

Historically the settings were stored in `TenantSettings` under
`app.models.core`. The data was consolidated into `CompanySettings`
(`app.models.company.company_settings`). This module re-exports that
model so the existing routers and use cases can keep importing
`TenantSettings` without failing.
"""

from app.models.company.company_settings import CompanySettings


def _get_locale(self) -> str | None:
    """Expose legacy `locale` attribute (maps to default_language)."""
    return getattr(self, "default_language", None)


def _set_locale(self, value: str | None) -> None:
    setattr(self, "default_language", value)


# Add the compatibility property only if it is not already present
if not hasattr(CompanySettings, "locale"):
    CompanySettings.locale = property(_get_locale, _set_locale)  # type: ignore[attr-defined]

# Legacy alias
TenantSettings = CompanySettings

__all__ = ["TenantSettings"]
