"""
Settings Router - System Configuration Management
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.models.company.company_settings import CompanySettings
from app.models.core.module import CompanyModule, Module
from app.modules.settings.application.modules_catalog import (
    AVAILABLE_MODULES,
    canonicalize_module_id,
    get_available_modules,
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


@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def get_all_settings(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Get all tenant settings"""
    tenant_id = UUID(tenant_id)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}
    enabled_modules = _canonical_enabled_list(
        base.get("enabled_modules", []) if isinstance(base, dict) else []
    )

    return {
        "tenant_id": str(tenant_id),
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
    tenant_id = UUID(tenant_id)

    module = _canonical_module_or_404(module)

    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()

    if not settings:
        return {}

    base = settings.settings if isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}
    module_config = config.get(module, {}) if isinstance(config, dict) else {}

    return {
        "module": module,
        "enabled": module
        in _canonical_enabled_list(
            base.get("enabled_modules", []) if isinstance(base, dict) else []
        ),
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
    tenant_id = UUID(tenant_id)

    module = _canonical_module_or_404(module)

    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="company_settings_missing")

    base = settings.settings if isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}
    enabled_modules = _canonical_enabled_list(
        base.get("enabled_modules", []) if isinstance(base, dict) else []
    )

    update_data = settings_in.model_dump(exclude_unset=True)
    config[module] = update_data
    base["config"] = config
    settings.settings = base

    db.commit()
    db.refresh(settings)

    return {
        "module": module,
        "enabled": module in enabled_modules,
        "config": config[module],
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
    tenant_id = UUID(tenant_id)

    module = _canonical_module_or_404(module)

    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="company_settings_missing")

    base = settings.settings if isinstance(settings.settings, dict) else {}
    enabled_modules = _canonical_enabled_list(
        list(base.get("enabled_modules", [])) if isinstance(base, dict) else []
    )

    if module not in enabled_modules:
        enabled_modules.append(module)
        base["enabled_modules"] = enabled_modules
        settings.settings = base
        db.commit()
        db.refresh(settings)

    return {
        "module": module,
        "enabled": True,
        "message": f"Module '{AVAILABLE_MODULES[module]['name']}' enabled successfully",
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
    tenant_id = UUID(tenant_id)

    module = _canonical_module_or_404(module)

    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    enabled_modules = _canonical_enabled_list(
        list(base.get("enabled_modules", [])) if isinstance(base, dict) else []
    )

    if not settings or not enabled_modules:
        return {
            "module": module,
            "enabled": False,
            "message": "Module is already disabled",
        }

    if module in enabled_modules:
        enabled_modules.remove(module)
        base["enabled_modules"] = enabled_modules
        settings.settings = base
        db.commit()
        db.refresh(settings)

    return {
        "module": module,
        "enabled": False,
        "message": f"Module '{AVAILABLE_MODULES[module]['name']}' disabled successfully",
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
    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == UUID(tenant_id)).first()
    )
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    enabled_modules = {
        canonical
        for module_name in (base.get("enabled_modules", []) if isinstance(base, dict) else [])
        if (canonical := canonicalize_module_id(module_name))
    }

    # Fallback: when company_settings has not been synchronized yet, derive enabled
    # modules from real tenant assignments (company_modules -> modules).
    if not enabled_modules:
        assigned_names = (
            db.query(Module.name)
            .join(CompanyModule, CompanyModule.module_id == Module.id)
            .filter(CompanyModule.tenant_id == UUID(tenant_id), CompanyModule.active)
            .all()
        )
        for (name,) in assigned_names:
            canonical = canonicalize_module_id(name)
            if canonical:
                enabled_modules.add(canonical)

    # Use the official catalog to keep names/icons/deps aligned
    modules_catalog = get_available_modules(db=db)

    def map_module(m: dict) -> dict:
        mid = m.get("id") or m.get("code")
        return {
            "id": mid,
            "code": m.get("code") or mid,
            "name": m.get("name"),
            "description": m.get("description"),
            "category": m.get("category"),
            "icon": m.get("icon"),
            "required": bool(m.get("required")),
            "default_enabled": bool(m.get("default_enabled")),
            "dependencies": m.get("dependencies") or [],
            "is_enabled": mid in enabled_modules,
        }

    # Solo devolver módulos contratados/habilitados para el tenant
    modules = [
        map_module(m) for m in modules_catalog if (m.get("id") or m.get("code")) in enabled_modules
    ]

    return {"modules": modules, "total": len(modules)}
