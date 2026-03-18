from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.tenant import Tenant
from app.modules.feature_flags.service import resolve_flags

router = APIRouter(
    prefix="/companies/{tenant_id}/feature-flags",
    tags=["Admin Feature Flags"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class FeatureFlagsUpdateIn(BaseModel):
    overrides: dict[str, bool | None]


def _validate_tenant_id(tenant_id: str) -> str:
    try:
        return str(UUID(str(tenant_id)))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_tenant_id") from exc


def _load_plan_name(db: Session, tenant_id: str) -> str | None:
    try:
        row = db.execute(
            text(
                """
                SELECT sp.name
                FROM tenant_subscriptions ts
                JOIN subscription_plans sp ON sp.id = ts.plan_id
                WHERE ts.tenant_id = :tenant_id
                  AND ts.status IN ('active', 'trialing', 'past_due')
                ORDER BY ts.created_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).first()
        return str(row[0]).lower() if row and row[0] else None
    except Exception:
        return None


def _resolved_payload(db: Session, tenant_id: str) -> dict[str, Any]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    config_json = tenant.config_json if isinstance(tenant.config_json, dict) else {}
    tenant_overrides = config_json.get("features")
    if not isinstance(tenant_overrides, dict):
        tenant_overrides = {}

    resolved = resolve_flags(
        tenant_id=tenant_id,
        country_code=getattr(tenant, "country_code", None),
        plan=_load_plan_name(db, tenant_id),
        tenant_features=tenant_overrides,
    )
    return {
        "tenant_id": tenant_id,
        "flags": resolved.to_dict(),
        "source": dict(resolved.source),
        "tenant_overrides": {k: v for k, v in tenant_overrides.items() if isinstance(v, bool)},
    }


@router.get("")
def get_feature_flags_admin(tenant_id: str, db: Session = Depends(get_db)):
    tenant_id = _validate_tenant_id(tenant_id)
    return _resolved_payload(db, tenant_id)


@router.put("")
def update_feature_flags_admin(
    tenant_id: str,
    payload: FeatureFlagsUpdateIn,
    db: Session = Depends(get_db),
):
    tenant_id = _validate_tenant_id(tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    config_json = tenant.config_json if isinstance(tenant.config_json, dict) else {}
    features = config_json.get("features")
    if not isinstance(features, dict):
        features = {}

    for flag_name, value in payload.overrides.items():
        normalized = str(flag_name or "").strip()
        if not normalized:
            continue
        if value is None:
            features.pop(normalized, None)
        else:
            features[normalized] = bool(value)

    if features:
        config_json["features"] = features
    else:
        config_json.pop("features", None)

    tenant.config_json = config_json
    db.commit()
    db.refresh(tenant)
    return _resolved_payload(db, tenant_id)
