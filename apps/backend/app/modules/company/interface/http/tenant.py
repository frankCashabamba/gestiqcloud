from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.dependencies import get_tenant_uuid
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


@router.get("", response_model=list[CompanyOutSchema])
def my_company(request: Request, db: Session = Depends(get_db)) -> list[CompanyOutSchema]:
    tenant_id = get_tenant_uuid(request)
    use = ListCompaniesTenant(SqlCompanyRepo(db))
    items = use.execute(tenant_id=tenant_id)
    return [CompanyOutSchema.model_validate(i) for i in items]
