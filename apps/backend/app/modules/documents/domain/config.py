from __future__ import annotations

from pydantic import BaseModel


class TenantDocConfig(BaseModel):
    country: str = "EC"
    document_mode_default: str = "TICKET_NO_FISCAL"
    render_format_default: str = "THERMAL_80MM"
    buyer_policy: dict = {}
    tax_profile: dict = {}
    branding: dict = {}
    template_overrides: dict = {}
    locale: str = "es-EC"
    config_version: int = 1
    effective_from: str | None = None
    id_types: list[str] = []
    tax_codes: dict = {}
