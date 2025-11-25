"""
Settings Router - System Configuration Management
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.core.settings import TenantSettings
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
    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    if not settings:
        settings = TenantSettings(
            tenant_id=tenant_id,
            config={},
            enabled_modules=[],
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    # TODO: Adaptar al schema TenantSettingsResponse completo
    return {
        "tenant_id": str(settings.tenant_id),
        "config": settings.config or {},
        "enabled_modules": settings.enabled_modules or [],
        "created_at": settings.created_at.isoformat() if settings.created_at else None,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
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

    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    if not settings:
        return {}

    module_config = settings.config.get(module, {}) if settings.config else {}

    return {
        "module": module,
        "enabled": module in (settings.enabled_modules or []),
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

    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    if not settings:
        settings = TenantSettings(
            tenant_id=tenant_id,
            config={},
            enabled_modules=[],
        )
        db.add(settings)

    if settings.config is None:
        settings.config = {}

    # Actualizar solo los campos presentes en settings_in
    update_data = settings_in.model_dump(exclude_unset=True)
    settings.config[module] = update_data

    db.commit()
    db.refresh(settings)

    return {
        "module": module,
        "enabled": module in (settings.enabled_modules or []),
        "config": settings.config[module],
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

    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    if not settings:
        settings = TenantSettings(
            tenant_id=tenant_id,
            config={},
            enabled_modules=[],
        )
        db.add(settings)

    if settings.enabled_modules is None:
        settings.enabled_modules = []

    if module not in settings.enabled_modules:
        settings.enabled_modules.append(module)
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

    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    if not settings or not settings.enabled_modules:
        return {
            "module": module,
            "enabled": False,
            "message": "Módulo ya está desactivado",
        }

    if module in settings.enabled_modules:
        settings.enabled_modules.remove(module)
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

    settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()

    enabled_modules = settings.enabled_modules if settings else []

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
