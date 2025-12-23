"""
Admin endpoints para editar configuración de sectores sin redeploy (FASE 6)

Endpoints:
- GET  /api/v1/admin/sectors/{code}/config    # Obtener config actual
- PUT  /api/v1/admin/sectors/{code}/config    # Actualizar config
"""

from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.config.database import get_db
from app.models.company.company import SectorTemplate
from app.schemas.sector_plantilla import SectorConfigUpdateRequest, SectorConfigResponse, SectorConfigJSON
from app.services.sector_service import get_sector_or_404
from app.services.cache import invalidate_sector_cache

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Sector Config"])


@router.get(
    "/sectors/{code}/config",
    response_model=SectorConfigResponse,
    summary="Obtener configuración actual de un sector"
)
def get_admin_sector_config(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración completa de un sector para el editor de admin.
    
    Args:
        code: Código del sector (ej: panaderia, taller)
        
    Returns:
        Configuración completa con metadatos de auditoría
    """
    try:
        sector = get_sector_or_404(code, db)
        
        # Parsear config JSON
        config = sector.template_config or {}
        
        return SectorConfigResponse(
            code=sector.code or code.lower(),
            name=sector.name,
            config=config,
            last_modified=sector.updated_at.isoformat() if sector.updated_at else None,
            modified_by=sector.updated_by,
            config_version=sector.config_version or 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración del sector: {str(e)}"
        ) from e


@router.put(
    "/sectors/{code}/config",
    response_model=dict,
    summary="Actualizar configuración de un sector"
)
def update_admin_sector_config(
    code: str,
    payload: SectorConfigUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración completa de un sector.
    
    Los cambios se guardan en la BD y se invalida el cache
    para que los usuarios vean los cambios al instante.
    
    Args:
        code: Código del sector
        payload: Nueva configuración (validada con Pydantic)
        
    Returns:
        Confirmación de actualización con timestamp y versión
        
    Raises:
        HTTPException 404: Sector no encontrado
        HTTPException 400: Configuración inválida
        HTTPException 500: Error al guardar
    """
    try:
        sector = get_sector_or_404(code, db)
        
        # Validar que la config sea válida (Pydantic ya lo hace en SectorConfigUpdateRequest)
        # Pero podemos hacer validaciones adicionales aquí
        validate_sector_config(payload.config)
        
        # Actualizar el modelo
        sector.template_config = payload.config.model_dump(mode='python')
        sector.updated_at = datetime.now(UTC)
        sector.updated_by = "admin"  # TODO: obtener del current_user cuando implemente auth
        sector.config_version = (sector.config_version or 1) + 1
        
        # Guardar en BD
        db.add(sector)
        db.commit()
        db.refresh(sector)
        
        # Invalidar cache
        invalidate_sector_cache(code)
        
        return {
            "success": True,
            "message": f"Configuración actualizada para sector '{code}'",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": sector.config_version,
            "sector_code": sector.code or code.lower()
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Configuración inválida: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando configuración: {str(e)}"
        ) from e


def validate_sector_config(config: SectorConfigJSON) -> None:
    """
    Validaciones adicionales de configuración (más allá del schema Pydantic)
    
    Args:
        config: Configuración a validar
        
    Raises:
        ValueError: Si la configuración es inválida
    """
    # Validar que tenga las secciones mínimas requeridas
    required_sections = ['branding', 'defaults', 'modules']
    for section in required_sections:
        if section not in dir(config) or getattr(config, section) is None:
            raise ValueError(f"Sección requerida faltante: {section}")
    
    # Validar colores hexadecimales
    if config.branding and config.branding.color_primario:
        if not is_valid_hex_color(config.branding.color_primario):
            raise ValueError(f"Color inválido: {config.branding.color_primario}")
    
    # Validar que icon no esté vacío
    if config.branding and not config.branding.icon:
        raise ValueError("El icon de branding no puede estar vacío")


def is_valid_hex_color(color: str) -> bool:
    """Valida que un string sea un color hexadecimal válido"""
    if not isinstance(color, str):
        return False
    if not color.startswith('#'):
        return False
    if len(color) != 7:
        return False
    try:
        int(color[1:], 16)
        return True
    except ValueError:
        return False
