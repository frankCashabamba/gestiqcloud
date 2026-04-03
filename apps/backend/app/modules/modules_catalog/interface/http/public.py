from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.tenant import Tenant as Empresa
from app.modules import crud as mod_crud
from app.modules.modules_catalog.interface.http.schemas import ModuloOutSchema
from app.modules.settings.application.modules_catalog import (
    is_standalone_module,
    resolve_module_runtime_meta,
)

router = APIRouter(
    prefix="/modules",
    tags=["Modules Public"],
)


@router.get("/company/{company_slug}/selectable", response_model=list[ModuloOutSchema])
def list_active_modules_by_slug(
    company_slug: str | None = None,
    db: Session = Depends(get_db),
):
    company = db.query(Empresa).filter(Empresa.slug == company_slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    registros = mod_crud.obtener_modulos_de_empresa(db, company.id)
    items: list[ModuloOutSchema] = []
    for r in registros:
        m = getattr(r, "module", None)
        if not r.active or m is None:
            continue
        if not is_standalone_module(
            getattr(m, "url", None) or getattr(m, "name", None),
            context_filters=getattr(m, "context_filters", None) or {},
        ):
            continue
        dto = {
            "id": m.id,
            "name": m.name,
            "url": m.url,
            "icon": m.icon or "",
            "category": m.category or "",
            **resolve_module_runtime_meta(
                getattr(m, "url", None) or getattr(m, "name", None),
                context_filters=getattr(m, "context_filters", None) or {},
            ),
            "active": m.active,
        }
        items.append(ModuloOutSchema.model_construct(**dto))
    return items
