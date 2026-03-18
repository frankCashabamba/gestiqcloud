"""
Settings Router - System Configuration Management
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.models.company.company_settings import CompanySettings
from app.models.core.module import CompanyModule, Module
from app.modules.settings.application.modules_catalog import (
    AVAILABLE_MODULES,
    canonicalize_module_id,
    get_available_modules,
    get_module_aliases,
    validate_module_dependencies,
)
from app.schemas.settings import ModuleSettingsUpdate

# NOTE: main.py already mounts this router with prefix="/api/v1".
# Using only "/settings" here avoids a double "/api/v1/api/v1" prefix that causes 404s.
router = APIRouter(prefix="/settings", tags=["Settings"])


def _canonical_module_or_404(module: str) -> str:
    canonical = canonicalize_module_id(module)
    if not canonical or canonical not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module}' not found",
        )
    return canonical


def _canonical_enabled_list(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        canonical = canonicalize_module_id(value)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def _settings_payload(settings: CompanySettings | None) -> dict[str, Any]:
    if not settings or not isinstance(settings.settings, dict):
        return {}
    return dict(settings.settings)


def _module_catalog_id(module_row: Module) -> str | None:
    context_filters = getattr(module_row, "context_filters", None) or {}
    for raw in (
        context_filters.get("catalog_id"),
        getattr(module_row, "url", None),
        getattr(module_row, "name", None),
    ):
        canonical = canonicalize_module_id(raw)
        if canonical:
            return canonical
    return None


def _find_module_row(db: Session, module: str) -> Module | None:
    canonical = _canonical_module_or_404(module)
    aliases = {alias.lower() for alias in get_module_aliases(canonical)}
    aliases.add(canonical)
    rows = (
        db.query(Module)
        .filter(
            or_(
                func.lower(Module.name).in_(aliases),
                func.lower(Module.url).in_(aliases),
            )
        )
        .all()
    )
    for row in rows:
        if _module_catalog_id(row) == canonical:
            return row
    return rows[0] if rows else None


def _load_company_module_state(
    db: Session, tenant_id: UUID, settings: CompanySettings | None
) -> tuple[list[str], list[str]]:
    rows = (
        db.query(CompanyModule, Module)
        .join(Module, CompanyModule.module_id == Module.id)
        .filter(CompanyModule.tenant_id == tenant_id)
        .all()
    )
    if rows:
        available_ids: list[str] = []
        active_ids: list[str] = []
        seen_available: set[str] = set()
        seen_active: set[str] = set()
        for company_module, module_row in rows:
            catalog_id = _module_catalog_id(module_row)
            if not catalog_id:
                continue
            if catalog_id not in seen_available:
                seen_available.add(catalog_id)
                available_ids.append(catalog_id)
            if company_module.active and catalog_id not in seen_active:
                seen_active.add(catalog_id)
                active_ids.append(catalog_id)
        return available_ids, active_ids

    fallback_active = _canonical_enabled_list(
        _settings_payload(settings).get("enabled_modules", [])
    )
    return list(fallback_active), list(fallback_active)


def _sync_enabled_modules_shadow(
    settings: CompanySettings | None, enabled_modules: list[str]
) -> bool:
    if not settings:
        return False
    base = _settings_payload(settings)
    canonical_enabled = _canonical_enabled_list(enabled_modules)
    if base.get("enabled_modules") == canonical_enabled:
        return False
    base["enabled_modules"] = canonical_enabled
    settings.settings = base
    return True


def _set_company_module_enabled(
    db: Session, tenant_id: UUID, module_row: Module, enabled: bool
) -> CompanyModule:
    assignment = (
        db.query(CompanyModule)
        .filter(
            CompanyModule.tenant_id == tenant_id,
            CompanyModule.module_id == module_row.id,
        )
        .first()
    )
    if assignment is None:
        assignment = CompanyModule(
            tenant_id=tenant_id,
            module_id=module_row.id,
            active=enabled,
        )
        db.add(assignment)
    else:
        assignment.active = enabled
    return assignment


@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def get_all_settings(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Get all tenant settings"""
    tenant_uuid = UUID(tenant_id)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    base = _settings_payload(settings)
    config = base.get("config", {}) if isinstance(base, dict) else {}
    _, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)
    if _sync_enabled_modules_shadow(settings, enabled_modules):
        db.commit()
        db.refresh(settings)

    return {
        "tenant_id": str(tenant_uuid),
        "config": config,
        "enabled_modules": enabled_modules,
        "created_at": settings.created_at.isoformat() if settings and settings.created_at else None,
        "updated_at": settings.updated_at.isoformat() if settings and settings.updated_at else None,
    }


@router.get("/modules/{module}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_module_settings(
    module: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Get configuration for a specific module"""
    tenant_uuid = UUID(tenant_id)
    canonical_module = _canonical_module_or_404(module)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    base = _settings_payload(settings)
    config = base.get("config", {}) if isinstance(base, dict) else {}
    module_config = config.get(canonical_module, {}) if isinstance(config, dict) else {}
    _, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)

    return {
        "module": canonical_module,
        "enabled": canonical_module in enabled_modules,
        "config": module_config,
    }


@router.put("/modules/{module}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def update_module_settings(
    module: str,
    settings_in: ModuleSettingsUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Update module configuration"""
    tenant_uuid = UUID(tenant_id)
    canonical_module = _canonical_module_or_404(module)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    if not settings:
        raise HTTPException(status_code=404, detail="company_settings_missing")

    base = _settings_payload(settings)
    config = base.get("config", {}) if isinstance(base, dict) else {}
    _, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)

    update_data = settings_in.model_dump(exclude_unset=True)
    config[canonical_module] = update_data
    base["config"] = config
    settings.settings = base

    db.commit()
    db.refresh(settings)

    return {
        "module": canonical_module,
        "enabled": canonical_module in enabled_modules,
        "config": config[canonical_module],
        "message": "Configuration updated successfully",
    }


@router.post(
    "/modules/{module}/enable", response_model=dict[str, Any], status_code=status.HTTP_200_OK
)
def enable_module(
    module: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Enable a module"""
    tenant_uuid = UUID(tenant_id)
    canonical_module = _canonical_module_or_404(module)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    _, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)

    test_enabled = _canonical_enabled_list([*enabled_modules, canonical_module])
    missing_dependencies = validate_module_dependencies(test_enabled)
    if canonical_module in missing_dependencies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "missing_dependencies",
                "module": canonical_module,
                "missing": missing_dependencies[canonical_module],
            },
        )

    module_row = _find_module_row(db, canonical_module)
    if module_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{canonical_module}' not found in catalog",
        )

    _set_company_module_enabled(db, tenant_uuid, module_row, True)
    _sync_enabled_modules_shadow(settings, test_enabled)
    db.commit()

    return {
        "module": canonical_module,
        "enabled": True,
        "message": f"Module '{AVAILABLE_MODULES[canonical_module]['name']}' enabled successfully",
    }


@router.post(
    "/modules/{module}/disable", response_model=dict[str, Any], status_code=status.HTTP_200_OK
)
def disable_module(
    module: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Disable a module"""
    tenant_uuid = UUID(tenant_id)
    canonical_module = _canonical_module_or_404(module)
    module_info = AVAILABLE_MODULES[canonical_module]
    if bool(module_info.get("required")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "module_required", "module": canonical_module},
        )

    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    _, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)
    if canonical_module not in enabled_modules:
        return {
            "module": canonical_module,
            "enabled": False,
            "message": "Module is already disabled",
        }

    remaining_enabled = [
        module_id for module_id in enabled_modules if module_id != canonical_module
    ]
    dependent_modules = [
        module_id
        for module_id in remaining_enabled
        if canonical_module in (AVAILABLE_MODULES.get(module_id, {}).get("dependencies") or [])
    ]
    if dependent_modules:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "module_has_dependents",
                "module": canonical_module,
                "dependents": dependent_modules,
            },
        )

    module_row = _find_module_row(db, canonical_module)
    if module_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{canonical_module}' not found in catalog",
        )

    _set_company_module_enabled(db, tenant_uuid, module_row, False)
    _sync_enabled_modules_shadow(settings, remaining_enabled)
    db.commit()

    return {
        "module": canonical_module,
        "enabled": False,
        "message": f"Module '{AVAILABLE_MODULES[canonical_module]['name']}' disabled successfully",
    }


@router.get("/modules", response_model=dict, status_code=status.HTTP_200_OK)
def list_modules(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """
    List all available modules for the tenant, marking which ones are enabled.

    Uses ensure_tenant to work in development even without explicit token (falls back to first tenant).
    """
    tenant_uuid = UUID(tenant_id)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
    available_modules, enabled_modules = _load_company_module_state(db, tenant_uuid, settings)
    available_set = set(available_modules)
    enabled_set = set(enabled_modules)
    if _sync_enabled_modules_shadow(settings, enabled_modules):
        db.commit()
        db.refresh(settings)

    modules_catalog = get_available_modules(db=db)

    def map_module(module_meta: dict[str, Any]) -> dict[str, Any]:
        module_id = module_meta.get("id") or module_meta.get("code")
        return {
            "id": module_id,
            "code": module_meta.get("code") or module_id,
            "name": module_meta.get("name"),
            "description": module_meta.get("description"),
            "category": module_meta.get("category"),
            "icon": module_meta.get("icon"),
            "required": bool(module_meta.get("required")),
            "default_enabled": bool(module_meta.get("default_enabled")),
            "dependencies": module_meta.get("dependencies") or [],
            "is_enabled": module_id in enabled_set,
        }

    modules = [
        map_module(module_meta)
        for module_meta in modules_catalog
        if (module_meta.get("id") or module_meta.get("code")) in available_set
    ]

    return {"modules": modules, "total": len(modules)}
