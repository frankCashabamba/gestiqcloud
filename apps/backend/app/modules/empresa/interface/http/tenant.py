from __future__ import annotations

from uuid import UUID

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.empresa.application.use_cases import ListarEmpresasTenant
from app.modules.empresa.infrastructure.repositories import SqlEmpresaRepo
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/empresa",
    tags=["Empresa"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


from app.modules.empresa.interface.http.schemas import EmpresaOutSchema


def _tenant_uuid(request: Request) -> UUID:
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


@router.get("", response_model=list[EmpresaOutSchema])
def mi_empresa(request: Request, db: Session = Depends(get_db)) -> list[EmpresaOutSchema]:
    tenant_id = _tenant_uuid(request)
    use = ListarEmpresasTenant(SqlEmpresaRepo(db))
    items = use.execute(tenant_id=tenant_id)
    return [EmpresaOutSchema.model_validate(i) for i in items]
