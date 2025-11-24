from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.usuarios.application import permissions, services
from app.modules.usuarios.infrastructure.schemas import (
    CompanyRoleOption,
    CompanyUserCreate,
    CompanyUserOut,
    CompanyUserUpdate,
    ModuleOption,
)

router = APIRouter(
    prefix="/tenant/users",
    tags=["Users"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)

public_router = APIRouter(prefix="/users", tags=["Users"])


def _tenant_id(request: Request) -> UUID:
    claims = request.state.access_claims
    tenant_id = claims.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_not_found_in_token")
    if isinstance(tenant_id, UUID):
        return tenant_id
    try:
        return UUID(str(tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.get("", response_model=list[CompanyUserOut])
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_id(request)
    return services.list_company_users(db, tenant_id)


@router.post("", response_model=CompanyUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    usuario_in: CompanyUserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_create_tenant_user),
):
    tenant_id = _tenant_id(request)
    return services.create_company_user(
        db,
        tenant_id,
        usuario_in,
        asignado_por_id=getattr(current_user, "user_id", None),
    )


@router.patch("/{usuario_id}", response_model=CompanyUserOut)
def update_user(
    request: Request,
    usuario_id: UUID,
    usuario_in: CompanyUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_id(request)
    return services.update_company_user(db, tenant_id, usuario_id, usuario_in)


@router.post("/{usuario_id}/set-password")
def set_user_password(
    request: Request,
    usuario_id: UUID,
    payload: SetPasswordIn,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_set_password_tenant_user),
):
    """Set the password for a company user in the same tenant."""
    tenant_id = _tenant_id(request)
    update = CompanyUserUpdate(password=payload.password)
    services.update_company_user(db, tenant_id, usuario_id, update)
    return {"ok": True}


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    request: Request,
    usuario_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_delete_tenant_user),
):
    tenant_id = _tenant_id(request)
    services.toggle_user_active(db, tenant_id, usuario_id, active=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/modules", response_model=list[ModuleOption])
def list_company_modules(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_id(request)
    return services.list_company_modules(db, tenant_id)


@router.get("/roles", response_model=list[CompanyRoleOption])
def list_company_roles(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_id(request)
    return services.list_company_roles(db, tenant_id)


@public_router.get("/check-username/{username}")
def check_username(username: str, db: Session = Depends(get_db)):
    disponible = services.check_username_availability(db, username)
    return {"available": disponible}
