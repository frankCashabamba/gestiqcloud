"""
Router para gestión de plantillas de sector
"""

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.ui_template import UiTemplate
from app.schemas.sector_plantilla import ApplySectorTemplateRequest
from app.services.sector_templates import (
    apply_sector_template,
    get_available_templates,
    get_template_preview,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Old URL: /api/v1/sectores (deprecated, kept for backward compatibility reference)
router = APIRouter(prefix="/api/v1/sectors", tags=["Plantillas de Sector"])


@router.get("/", summary="Listar plantillas de sector disponibles")
async def list_sector_templates(db: Session = Depends(get_db)):
    """
    Obtiene todas las plantillas de sector disponibles.

    Retorna información resumida de cada plantilla:
    - Nombre
    - Branding (color, plantilla inicio)
    - Número de módulos habilitados
    - Categorías por defecto
    """
    templates = get_available_templates(db)
    return {"count": len(templates), "templates": templates}


@router.get("/ui-plantillas", summary="Listar plantillas UI disponibles")
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
    summary="Crear plantilla UI",
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
    summary="Actualizar plantilla UI",
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
    summary="Eliminar plantilla UI",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)
async def delete_ui_template(slug: str, db: Session = Depends(get_db)):
    row = db.query(UiTemplate).filter(UiTemplate.slug == slug).first()
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/{sector_plantilla_id}", summary="Ver detalle de plantilla")
async def get_sector_template_detail(sector_plantilla_id: int, db: Session = Depends(get_db)):
    """
    Obtiene vista previa detallada de una plantilla de sector.

    Incluye toda la configuración que se aplicará si se selecciona:
    - Módulos habilitados/deshabilitados
    - Configuración de branding
    - Defaults (moneda, impuestos, categorías)
    - Configuración POS
    - Configuración inventario
    """
    try:
        preview = get_template_preview(db, sector_plantilla_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo plantilla: {str(e)}")


@router.post("/apply", summary="Aplicar plantilla de sector (solo diseño)")
async def apply_template_to_tenant(
    request: ApplySectorTemplateRequest, db: Session = Depends(get_db)
):
    """
    Aplica una plantilla de sector a un tenant existente en modo diseño únicamente.

    Acciones realizadas (design-only):
    - Actualiza branding (color primario, plantilla de inicio)
    - Actualiza metadatos `sector_plantilla_nombre`
    - Mergea `config_json` con sección `branding/defaults`

    No modifica módulos ni categorías. Use `override_existing: true` para sobrescribir config existente.
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
            "message": "Plantilla aplicada exitosamente",
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error aplicando plantilla: {str(e)}")
