"""
Feature flag resolution service.

Resolution order (last wins):
  1. Global defaults
  2. Environment overrides (FEATURE_FLAG_* env vars)
  3. Country overrides
  4. Plan overrides
  5. Tenant overrides (config_json.features)
  6. Beta user overrides
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_GLOBAL_DEFAULTS: dict[str, bool] = {
    "inventory_lot_tracking": False,
    "inventory_expiration": False,
    "production_enabled": False,
    "pos_enabled": True,
    "einvoicing_enabled": False,
    "crm_enabled": False,
    "hr_enabled": False,
    "webhooks_enabled": False,
    "copilot_enabled": True,
    "copilot_write_actions": False,
    "ocr_enabled": True,
    "ocr_vision_fallback": True,
    "billing_enabled": False,
    "express_mode": True,
    "progressive_disclosure": True,
    "audit_logging": True,
    "advanced_reports": False,
}

_COUNTRY_OVERRIDES: dict[str, dict[str, bool]] = {
    "EC": {"einvoicing_enabled": True},
    "CL": {"einvoicing_enabled": True},
    "ES": {"einvoicing_enabled": False},
}

_PLAN_OVERRIDES: dict[str, dict[str, bool]] = {
    "free": {
        "copilot_write_actions": False,
        "advanced_reports": False,
        "hr_enabled": False,
        "webhooks_enabled": False,
    },
    "starter": {"advanced_reports": True},
    "professional": {
        "copilot_write_actions": True,
        "advanced_reports": True,
        "hr_enabled": True,
        "webhooks_enabled": True,
    },
    "enterprise": {
        "copilot_write_actions": True,
        "advanced_reports": True,
        "hr_enabled": True,
        "webhooks_enabled": True,
    },
}

_ENV_PREFIX = "FEATURE_FLAG_"


@dataclass
class ResolvedFlags:
    flags: dict[str, bool] = field(default_factory=dict)
    source: dict[str, str] = field(default_factory=dict)

    def is_enabled(self, flag: str) -> bool:
        return self.flags.get(flag, False)

    def to_dict(self) -> dict[str, bool]:
        return dict(self.flags)


def _env_overrides() -> dict[str, bool]:
    overrides = {}
    for key, val in os.environ.items():
        if key.startswith(_ENV_PREFIX):
            flag_name = key[len(_ENV_PREFIX) :].lower()
            overrides[flag_name] = val.strip().lower() in ("1", "true", "yes")
    return overrides


def resolve_flags(
    *,
    tenant_id: str | None = None,
    country_code: str | None = None,
    plan: str | None = None,
    user_id: str | None = None,
    tenant_features: dict[str, Any] | None = None,
    beta_users: set[str] | None = None,
) -> ResolvedFlags:
    result = ResolvedFlags()

    for flag, val in _GLOBAL_DEFAULTS.items():
        result.flags[flag] = val
        result.source[flag] = "default"

    for flag, val in _env_overrides().items():
        result.flags[flag] = val
        result.source[flag] = "env"

    if country_code and country_code.upper() in _COUNTRY_OVERRIDES:
        for flag, val in _COUNTRY_OVERRIDES[country_code.upper()].items():
            result.flags[flag] = val
            result.source[flag] = f"country:{country_code.upper()}"

    if plan and plan.lower() in _PLAN_OVERRIDES:
        for flag, val in _PLAN_OVERRIDES[plan.lower()].items():
            result.flags[flag] = val
            result.source[flag] = f"plan:{plan.lower()}"

    if tenant_features and isinstance(tenant_features, dict):
        for flag, val in tenant_features.items():
            if isinstance(val, bool):
                result.flags[flag] = val
                result.source[flag] = f"tenant:{tenant_id or 'unknown'}"

    if user_id and beta_users and user_id in beta_users:
        for flag in ("copilot_write_actions", "advanced_reports"):
            result.flags[flag] = True
            result.source[flag] = f"beta_user:{user_id}"

    return result


def get_tenant_flags(db: Session, tenant_id: str) -> ResolvedFlags:
    from sqlalchemy import text

    country_code = None
    tenant_features = None

    try:
        row = db.execute(
            text("SELECT country_code, config_json FROM tenants WHERE id = :tid"),
            {"tid": tenant_id},
        ).first()
        if row:
            country_code = row[0]
            config = row[1] or {}
            tenant_features = config.get("features") if isinstance(config, dict) else None
    except Exception:
        logger.warning("Failed to load tenant config for flags", exc_info=True)

    return resolve_flags(
        tenant_id=tenant_id,
        country_code=country_code,
        tenant_features=tenant_features,
    )
