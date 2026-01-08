"""
Settings Router - System Configuration Management
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.company.company_settings import CompanySettings
from app.schemas.settings import ModuleInfo, ModuleListResponse, ModuleSettingsUpdate

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

AVAILABLE_MODULES = {
    "inventory": {"name": "Inventory", "description": "Stock and warehouse management"},
    "sales": {"name": "Sales", "description": "Sales and customer management"},
    "purchases": {"name": "Purchases", "description": "Purchase and supplier management"},
    "pos": {"name": "Point of Sale", "description": "POS and cash register"},
    "finance": {"name": "Finance", "description": "Cash, bank, and accounting"},
    "hr": {"name": "Human Resources", "description": "Human resources and payroll"},
    "expenses": {"name": "Expenses", "description": "Operational expense control"},
    "einvoicing": {"name": "E-Invoicing", "description": "SRI/AEAT"},
}


@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def get_all_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all tenant settings"""
    tenant_id = UUID(current_user["tenant_id"])
    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}
    enabled_modules = base.get("enabled_modules", []) if isinstance(base, dict) else []

    return {
        "tenant_id": str(tenant_id),
        "config": config,
        "enabled_modules": enabled_modules,
        "created_at": settings.created_at.isoformat() if settings and settings.created_at else None,
        "updated_at": settings.updated_at.isoformat() if settings and settings.updated_at else None,
    }


@router.get("/{module}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_module_settings(
    module: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtener configuración de un módulo específico"""
    tenant_id = UUID(current_user["tenant_id"])

    if module not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Módulo '{module}' no encontrado",
        )

    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )

    if not settings:
        return {}

    base = settings.settings if isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}
    module_config = config.get(module, {}) if isinstance(config, dict) else {}

    return {
        "module": module,
        "enabled": module in (base.get("enabled_modules", []) if isinstance(base, dict) else []),
        "config": module_config,
    }


@router.put("/{module}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def update_module_settings(
    module: str,
    settings_in: ModuleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualizar configuración de un módulo"""
    tenant_id = UUID(current_user["tenant_id"])

    if module not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Módulo '{module}' no encontrado",
        )

    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not settings:
        raise HTTPException(status_code=404, detail="company_settings_missing")

    base = settings.settings if isinstance(settings.settings, dict) else {}
    config = base.get("config", {}) if isinstance(base, dict) else {}

    # Actualizar solo los campos presentes en settings_in
    update_data = settings_in.model_dump(exclude_unset=True)
    config[module] = update_data
    base["config"] = config
    settings.settings = base

    db.commit()
    db.refresh(settings)

    return {
        "module": module,
        "enabled": module in (base.get("enabled_modules", []) if isinstance(base, dict) else []),
        "config": config[module],
        "message": "Configuración actualizada exitosamente",
    }


@router.post("/{module}/enable", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def enable_module(
    module: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Activar un módulo"""
    tenant_id = UUID(current_user["tenant_id"])

    if module not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Módulo '{module}' no encontrado",
        )

    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not settings:
        raise HTTPException(status_code=404, detail="company_settings_missing")

    base = settings.settings if isinstance(settings.settings, dict) else {}
    enabled_modules = list(base.get("enabled_modules", [])) if isinstance(base, dict) else []

    if module not in enabled_modules:
        enabled_modules.append(module)
        base["enabled_modules"] = enabled_modules
        settings.settings = base
        db.commit()
        db.refresh(settings)

    return {
        "module": module,
        "enabled": True,
        "message": f"Módulo '{AVAILABLE_MODULES[module]['name']}' activado exitosamente",
    }


@router.post("/{module}/disable", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def disable_module(
    module: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Desactivar un módulo"""
    tenant_id = UUID(current_user["tenant_id"])

    if module not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Módulo '{module}' no encontrado",
        )

    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    enabled_modules = list(base.get("enabled_modules", [])) if isinstance(base, dict) else []

    if not settings or not enabled_modules:
        return {
            "module": module,
            "enabled": False,
            "message": "Módulo ya está desactivado",
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
        "message": f"Módulo '{AVAILABLE_MODULES[module]['name']}' desactivado exitosamente",
    }


@router.get("/modules", response_model=ModuleListResponse, status_code=status.HTTP_200_OK)
def list_modules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Listar todos los módulos disponibles"""
    tenant_id = UUID(current_user["tenant_id"])

    settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    base = settings.settings if settings and isinstance(settings.settings, dict) else {}
    enabled_modules = base.get("enabled_modules", []) if isinstance(base, dict) else []

    modules = [
        ModuleInfo(
            key=key,
            name=info["name"],
            description=info["description"],
            enabled=key in (enabled_modules or []),
        )
        for key, info in AVAILABLE_MODULES.items()
    ]

    return ModuleListResponse(modules=modules)

