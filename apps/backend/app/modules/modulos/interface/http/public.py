from __future__ import annotations

from app.config.database import get_db
from app.models.tenant import Tenant as Empresa
from app.modules import crud as mod_crud
from app.modules.modulos.interface.http.schemas import ModuloOutSchema
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/modulos",
    tags=["Modulos Public"],
)


@router.get("/empresa/{empresa_slug}/seleccionables", response_model=list[ModuloOutSchema])
def listar_modulos_activos_por_slug(
    empresa_slug: str | None = None,
    db: Session = Depends(get_db),
):
    empresa = db.query(Empresa).filter(Empresa.slug == empresa_slug).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    registros = mod_crud.obtener_modulos_de_empresa(db, empresa.id)
    items: list[ModuloOutSchema] = []
    for r in registros:
        m = getattr(r, "modulo", None)
        if not r.activo or m is None:
            continue
        dto = {
            "id": m.id,
            "name": m.name,
            "nombre": m.name,  # Legacy compatibility
            "url": m.url,
            "icono": m.icono,
            "categoria": m.categoria,
            "active": m.active,
            "activo": m.active,  # Legacy compatibility
        }
        items.append(ModuloOutSchema.model_construct(**dto))
    return items
