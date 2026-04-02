# app/api/v1e/profile.py
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant

router = APIRouter(
    prefix="/me",
    tags=["Me"],
    dependencies=[Depends(with_access_claims), Depends(ensure_rls)],
)

_GENERIC_TENANT_NAMES = {"default", "tenant", "empresa", "mi empresa", "tu empresa"}
_GENERIC_TENANT_SLUGS = {"", "default", "tenant", "empresa"}


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _extract_settings_map(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_generic_tenant_name(value: Any) -> bool:
    return not _has_text(value) or str(value).strip().lower() in _GENERIC_TENANT_NAMES


def _is_generic_tenant_slug(value: Any) -> bool:
    return not _has_text(value) or str(value).strip().lower() in _GENERIC_TENANT_SLUGS


def _infer_onboarding_complete(
    company_settings: CompanySettings | None, tenant: Tenant | None
) -> bool:
    settings_map = _extract_settings_map(getattr(company_settings, "settings", None))
    explicit_flag = bool(settings_map.get("onboarding_complete", False))

    has_named_tenant = (
        tenant is not None
        and not _is_generic_tenant_name(getattr(tenant, "name", None))
        and not _is_generic_tenant_slug(getattr(tenant, "slug", None))
    )
    has_company_profile = company_settings is not None and any(
        _has_text(getattr(company_settings, attr, None))
        for attr in ("company_name", "tax_id", "company_logo")
    )
    has_tenant_profile = tenant is not None and any(
        _has_text(getattr(tenant, attr, None))
        for attr in ("tax_id", "phone", "address", "city", "state", "postal_code", "website")
    )
    has_localized_settings = company_settings is not None and all(
        _has_text(getattr(company_settings, attr, None))
        for attr in ("default_language", "timezone", "currency")
    )
    has_legacy_settings_baseline = company_settings is not None and all(
        _has_text(getattr(company_settings, attr, None))
        for attr in (
            "default_language",
            "timezone",
            "currency",
            "primary_color",
            "secondary_color",
        )
    )

    return bool(
        explicit_flag
        or has_company_profile
        or has_tenant_profile
        or (has_named_tenant and has_localized_settings)
        or (not has_named_tenant and has_legacy_settings_baseline)
    )


@router.get("/tenant", dependencies=[Depends(require_scope("tenant"))])
def me_tenant(request: Request, response: Response, db: Session = Depends(get_db)):
    c = request.state.access_claims
    response.headers["Cache-Control"] = "private, no-store"
    tenant_id = c.get("tenant_id")
    onboarding_complete = False
    sector_nombre = None

    if tenant_id:
        try:
            tenant_uuid = UUID(str(tenant_id))
            tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
            settings = (
                db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
            )
            onboarding_complete = _infer_onboarding_complete(settings, tenant)
            sector_nombre = getattr(tenant, "sector_template_name", None) if tenant else None
        except Exception:
            onboarding_complete = False

    return {
        "user_id": c.get("user_id"),
        "tenant_id": tenant_id,
        "empresa_slug": c.get("empresa_slug"),
        "name": c.get("name"),
        "is_company_admin": c.get("is_company_admin"),
        "roles": c.get("roles", []),
        "permissions": c.get("permissions", {}),
        "plantilla": c.get("plantilla"),
        "onboarding_complete": onboarding_complete,
        "sector_nombre": sector_nombre,
    }


@router.get("/admin", dependencies=[Depends(require_scope("admin"))])
def me_admin(request: Request, response: Response):
    c = request.state.access_claims
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "user_id": c.get("user_id"),
        "is_superadmin": c.get("is_superadmin", True),
        "user_type": c.get("user_type", "superadmin"),
    }
