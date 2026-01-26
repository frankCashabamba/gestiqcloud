from __future__ import annotations

from apps.backend.app.shared.utils import ping_ok
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.modulo import CompanyModule, Module
from app.modules import crud as mod_crud
from app.modules import schemas as mod_schemas
from app.modules import services as mod_services
from app.modules.modulos.interface.http.schemas import ModuloOutSchema

router = APIRouter(
    prefix="/admin/modules",
    tags=["Admin Modules"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _module_to_response(m: Module) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "url": getattr(m, "url", None),
        "icon": getattr(m, "icon", None),
        "category": getattr(m, "category", None),
        "active": m.active,
        "description": getattr(m, "description", None),
        "initial_template": getattr(m, "initial_template", None),
        "context_type": getattr(m, "context_type", None),
        "target_model": getattr(m, "target_model", None),
        "context_filters": getattr(m, "context_filters", None) or {},
    }


@router.get("/ping")
def ping_admin_modules():
    return ping_ok()


@router.get("", response_model=list[ModuloOutSchema])
@router.get("/", response_model=list[ModuloOutSchema])
def listar_modulos_admin(db: Session = Depends(get_db)):
    modules = db.query(Module).filter(Module.active).order_by(Module.id.asc()).all()  # noqa: E712
    return [ModuloOutSchema.model_validate(_module_to_response(m)) for m in modules]


@router.get("/public", response_model=list[ModuloOutSchema])
def obtener_modulos_publicos(db: Session = Depends(get_db)):
    modules = mod_crud.listar_modulos_publicos(db)
    return [ModuloOutSchema.model_validate(_module_to_response(m)) for m in modules]


@router.get("/company/{tenant_id}", response_model=list[mod_schemas.EmpresaModuloOut])
def listar_modulos_de_empresa(tenant_id: str, db: Session = Depends(get_db)):
    registros = mod_crud.obtener_modulos_de_empresa(db, tenant_id)
    resultado: list[dict] = []
    for r in registros:
        modulo_payload = _module_to_response(r.module) if r.module else None
        resultado.append(
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "company_slug": r.tenant.slug if r.tenant else None,
                "active": getattr(r, "active", None),
                "activation_date": getattr(r, "activation_date", None),
                "module_id": r.module_id,
                "module": modulo_payload,
                "expiration_date": getattr(r, "expiration_date", None),
                "initial_template": getattr(r, "initial_template", None),
            }
        )
    return resultado


@router.post("/company/{tenant_id}/upsert", response_model=mod_schemas.EmpresaModuloOutAdmin)
def upsert_modulo_empresa(
    tenant_id: str,
    modulo_in: mod_schemas.EmpresaModuloCreate,
    db: Session = Depends(get_db),
):
    return mod_services.upsert_modulo_a_empresa(db, tenant_id, modulo_in)


@router.delete("/company/{tenant_id}/module/{modulo_id}")
def eliminar_modulo_de_empresa(tenant_id: str, modulo_id: str, db: Session = Depends(get_db)):
    empresa_modulo = (
        db.query(CompanyModule).filter_by(tenant_id=tenant_id, module_id=modulo_id).first()
    )
    if not empresa_modulo:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(empresa_modulo)
    db.commit()
    return {"ok": True}
