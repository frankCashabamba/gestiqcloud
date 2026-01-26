"""
Admin endpoints for editing sector configuration without redeploy (PHASE 6)

Endpoints:
- GET  /api/v1/admin/sectors/{code}/config    # Get current config
- PUT  /api/v1/admin/sectors/{code}/config    # Update config
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.sector_plantilla import (
    SectorConfigJSON,
    SectorConfigResponse,
    SectorConfigUpdateRequest,
)
from app.services.cache import invalidate_sector_cache
from app.services.sector_service import get_sector_or_404

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Sector Config"])


@router.get(
    "/sectors/{code}/config",
    response_model=SectorConfigResponse,
    summary="Get current sector configuration",
)
def get_admin_sector_config(code: str, db: Session = Depends(get_db)):
    """
    Gets the complete configuration of a sector for the admin editor.

    Args:
        code: Sector code (e.g., bakery, workshop)

    Returns:
        Complete configuration with audit metadata
    """
    try:
        sector = get_sector_or_404(code, db)

        config = sector.template_config or {}

        return SectorConfigResponse(
            code=sector.code or code.lower(),
            name=sector.name,
            config=config,
            last_modified=sector.updated_at.isoformat() if sector.updated_at else None,
            modified_by=sector.updated_by,
            config_version=sector.config_version or 1,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting sector configuration: {str(e)}",
        ) from e


@router.put(
    "/sectors/{code}/config",
    response_model=dict,
    summary="Update sector configuration",
)
def update_admin_sector_config(
    code: str,
    payload: SectorConfigUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates the complete configuration of a sector.

    Changes are saved to the database and the cache is invalidated
    so users see changes instantly.

    Args:
        code: Sector code
        payload: New configuration (validated with Pydantic)

    Returns:
        Update confirmation with timestamp and version

    Raises:
        HTTPException 404: Sector not found
        HTTPException 400: Invalid configuration
        HTTPException 500: Error saving
    """
    try:
        sector = get_sector_or_404(code, db)

        validate_sector_config(payload.config)

        sector.template_config = payload.config.model_dump(mode="python")
        sector.updated_at = datetime.now(UTC)
        sector.updated_by = "admin"  # TODO: get from current_user when auth is implemented
        sector.config_version = (sector.config_version or 1) + 1

        db.add(sector)
        db.commit()
        db.refresh(sector)

        invalidate_sector_cache(code)

        return {
            "success": True,
            "message": f"Configuration updated for sector '{code}'",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": sector.config_version,
            "sector_code": sector.code or code.lower(),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating configuration: {str(e)}",
        ) from e


def validate_sector_config(config: SectorConfigJSON) -> None:
    """
    Additional configuration validations (beyond the Pydantic schema)

    Args:
        config: Configuration to validate

    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ["branding", "defaults", "modules"]
    for section in required_sections:
        if section not in dir(config) or getattr(config, section) is None:
            raise ValueError(f"Required section missing: {section}")

    if config.branding and config.branding.color_primario:
        if not is_valid_hex_color(config.branding.color_primario):
            raise ValueError(f"Invalid color: {config.branding.color_primario}")

    if config.branding and not config.branding.color_secundario:
        raise ValueError("Secondary color required")

    if config.branding and config.branding.color_secundario:
        if not is_valid_hex_color(config.branding.color_secundario):
            raise ValueError(f"Invalid color: {config.branding.color_secundario}")

    if config.branding and not config.branding.icon:
        raise ValueError("Branding icon cannot be empty")


def is_valid_hex_color(color: str) -> bool:
    """Validates that a string is a valid hexadecimal color"""
    if not isinstance(color, str):
        return False
    if not color.startswith("#"):
        return False
    if len(color) != 7:
        return False
    try:
        int(color[1:], 16)
        return True
    except ValueError:
        return False
