from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.company.application.use_cases import ListCompaniesTenant
from app.modules.company.infrastructure.repositories import SqlCompanyRepo
from app.modules.company.interface.http.schemas import CompanyOutSchema

router = APIRouter(
    prefix="/company",
    tags=["Company"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_uuid(request: Request) -> UUID:
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="invalid_tenant_id")


@router.get("", response_model=list[CompanyOutSchema])
def my_company(request: Request, db: Session = Depends(get_db)) -> list[CompanyOutSchema]:
    tenant_id = _tenant_uuid(request)
    use = ListCompaniesTenant(SqlCompanyRepo(db))
    items = use.execute(tenant_id=tenant_id)
    return [CompanyOutSchema.model_validate(i) for i in items]
