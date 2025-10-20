from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.modulos.application.use_cases import ListarModulosAsignadosTenant
from app.modules.modulos.infrastructure.repositories import SqlModuloRepo
from app.modules.modulos.interface.http.schemas import ModuloOutSchema


router = APIRouter(
    prefix="/modulos",
    tags=["Modulos"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/", response_model=list[ModuloOutSchema])
def listar_modulos_asignados(request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    tenant_id = int(claims.get("tenant_id"))
    # Fallback a 'user_id' si falta 'tenant_user_id' en claims
    raw_uid = claims.get("tenant_user_id") or claims.get("user_id")
    tenant_user_id = int(raw_uid)
    use = ListarModulosAsignadosTenant(SqlModuloRepo(db))
    items = use.execute(tenant_user_id=tenant_user_id, tenant_id=tenant_id)
    return [ModuloOutSchema.model_construct(**i) for i in items]
