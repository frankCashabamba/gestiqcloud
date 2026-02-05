"""
Router for sector template management.

CONSOLIDATION IN PROGRESS:
- Configuration endpoints (/{code}/config, /{code}/full-config, /{code}/features, /{code}/fields/{module})
  are being consolidated in app/routers/sectors.py per PLAN_ELIMINACION_HARDCODING_COMPLETO.md
- This file maintains endpoints for template application and UI template management
- Backward compatibility: get_sector_config still works but is deprecated

See: app/routers/sectors.py for consolidated endpoints (PHASE 1)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.ui_template import UiTemplate
from app.schemas.sector_plantilla import ApplySectorTemplateRequest, SectorConfigJSON
from app.services.sector_service import get_sector_or_404
from app.services.sector_templates import (
    apply_sector_template,
    get_available_templates,
    get_template_preview,
)

router = APIRouter(prefix="/api/v1/sectors", tags=["Sector Templates"])


@router.get("/{code}/config", summary="Get sector branding (DEPRECATED)")
async def get_sector_config_deprecated(code: str, db: Session = Depends(get_db)):
    """
    DEPRECATED - Use GET /api/v1/sectors/{code}/config instead.

    This endpoint maintains backward compatibility but returns branding only.
    Use the consolidated endpoint in app/routers/sectors.py which returns
    full configuration per PLAN_ELIMINACION_HARDCODING_COMPLETO.md

    Gets only the sector branding configuration.

    Args:
        code: Sector code (bakery, workshop, retail, etc.)

    Returns:
        Sector branding configuration

    Example:
        GET /api/v1/sectors/bakery/config
    """
    try:
        sector = get_sector_or_404(code, db)

        config = SectorConfigJSON(**sector.template_config)
        return {
            "ok": True,
            "code": code.lower(),
            "sector_name": sector.name,
            "branding": config.branding.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error in sector configuration: {str(e)}"
        ) from e


@router.get("/", summary="List available sector templates")
async def list_sector_templates(db: Session = Depends(get_db)):
    """
    Gets all available sector templates.

    Returns summary information for each template:
    - Name
    - Branding (color, start template)
    - Number of enabled modules
    - Default categories
    """
    templates = get_available_templates(db)
    return {"count": len(templates), "templates": templates}


@router.get("/ui-plantillas", summary="List available UI templates")
async def list_ui_templates(db: Session = Depends(get_db)):
    rows = (
        db.query(UiTemplate)
        .filter(UiTemplate.active == True)  # noqa: E712
        .order_by(UiTemplate.ord.asc().nulls_last(), UiTemplate.label.asc())
        .all()
    )
    items = [
        {
            "slug": r.slug,
            "label": r.label,
            "description": r.description,
            "pro": bool(r.pro),
            "ord": r.ord,
        }
        for r in rows
    ]
    return {"count": len(items), "items": items}


class UiTemplateIn(BaseModel):
    slug: str
    label: str
    description: str | None = None
    pro: bool | None = False
    active: bool | None = True
    ord: int | None = None


@router.post(
    "/ui-plantillas",
    summary="Create UI template",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)
async def create_ui_template(payload: UiTemplateIn, db: Session = Depends(get_db)):
    exists = db.query(UiTemplate).filter(UiTemplate.slug == payload.slug).first()
    if exists:
        raise HTTPException(status_code=400, detail="slug_exists")
    row = UiTemplate(
        slug=payload.slug.strip().lower(),
        label=payload.label,
        description=payload.description,
        pro=bool(payload.pro or False),
        active=bool(payload.active if payload.active is not None else True),
        ord=payload.ord,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "item": {
            "slug": row.slug,
            "label": row.label,
            "description": row.description,
            "pro": bool(row.pro),
            "active": bool(row.active),
            "ord": row.ord,
        },
    }


@router.put(
    "/ui-plantillas/{slug}",
    summary="Update UI template",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)
async def update_ui_template(slug: str, payload: UiTemplateIn, db: Session = Depends(get_db)):
    row = db.query(UiTemplate).filter(UiTemplate.slug == slug).first()
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    row.slug = payload.slug.strip().lower()
    row.label = payload.label
    row.description = payload.description
    row.pro = bool(payload.pro or False)
    row.active = bool(payload.active if payload.active is not None else True)
    row.ord = payload.ord
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "item": {
            "slug": row.slug,
            "label": row.label,
            "description": row.description,
            "pro": bool(row.pro),
            "active": bool(row.active),
            "ord": row.ord,
        },
    }


@router.delete(
    "/ui-plantillas/{slug}",
    summary="Delete UI template",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)
async def delete_ui_template(slug: str, db: Session = Depends(get_db)):
    row = db.query(UiTemplate).filter(UiTemplate.slug == slug).first()
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/{sector_plantilla_id}", summary="View template detail")
async def get_sector_template_detail(sector_plantilla_id: int, db: Session = Depends(get_db)):
    """
    Gets detailed preview of a sector template.

    Includes all configuration that will be applied if selected:
    - Enabled/disabled modules
    - Branding configuration
    - Defaults (currency, taxes, categories)
    - POS configuration
    - Inventory configuration
    """
    try:
        preview = get_template_preview(db, sector_plantilla_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting template: {str(e)}")


@router.post("/apply", summary="Apply sector template (design only)")
async def apply_template_to_tenant(
    request: ApplySectorTemplateRequest, db: Session = Depends(get_db)
):
    """
    Applies a sector template to an existing tenant in design-only mode.

    Actions performed (design-only):
    - Updates branding (primary color, start template)
    - Updates metadata `sector_plantilla_nombre`
    - Merges `config_json` with `branding/defaults` section

    Does not modify modules or categories. Use `override_existing: true` to overwrite existing config.
    """
    try:
        result = apply_sector_template(
            db,
            request.tenant_id,
            request.sector_plantilla_id,
            request.override_existing,
            design_only=True,
        )

        db.commit()

        return {
            "success": True,
            "message": "Template applied successfully",
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error applying template: {str(e)}")
