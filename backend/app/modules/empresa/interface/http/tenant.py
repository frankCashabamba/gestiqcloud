from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.empresa.application.use_cases import ListarEmpresasTenant
from app.modules.empresa.infrastructure.repositories import SqlEmpresaRepo


router = APIRouter(
    prefix="/empresa",
    tags=["Empresa"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


from app.modules.empresa.interface.http.schemas import EmpresaOutSchema


@router.get("/", response_model=list[EmpresaOutSchema])
def mi_empresa(request: Request, db: Session = Depends(get_db)) -> list[EmpresaOutSchema]:
    claims = request.state.access_claims
    tenant_id = int(claims.get("tenant_id"))
    use = ListarEmpresasTenant(SqlEmpresaRepo(db))
    items = use.execute(tenant_id=tenant_id)
    return [EmpresaOutSchema.model_validate(i) for i in items]
