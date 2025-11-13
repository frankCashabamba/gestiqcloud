from uuid import UUID

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.usuarios.application import permissions, services
from app.modules.usuarios.infrastructure.schemas import (
    ModuloOption,
    RolEmpresaOption,
    UsuarioEmpresaCreate,
    UsuarioEmpresaOut,
    UsuarioEmpresaUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/tenant/usuarios",
    tags=["Usuarios"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)

public_router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _tenant_empresa_id(request: Request) -> UUID:
    claims = request.state.access_claims
    tenant_id = claims.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Empresa no encontrada en el token")
    if isinstance(tenant_id, UUID):
        return tenant_id
    try:
        return UUID(str(tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.get("", response_model=list[UsuarioEmpresaOut])
def listar_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    return services.listar_usuarios_empresa(db, tenant_id)


@router.post("", response_model=UsuarioEmpresaOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    request: Request,
    usuario_in: UsuarioEmpresaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_create_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    return services.crear_usuario_empresa(
        db,
        tenant_id,
        usuario_in,
        asignado_por_id=getattr(current_user, "user_id", None),
    )


@router.patch("/{usuario_id}", response_model=UsuarioEmpresaOut)
def actualizar_usuario(
    request: Request,
    usuario_id: UUID,
    usuario_in: UsuarioEmpresaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    return services.actualizar_usuario_empresa(db, tenant_id, usuario_id, usuario_in)


@router.post("/{usuario_id}/set-password")
def set_password_usuario(
    request: Request,
    usuario_id: UUID,
    payload: SetPasswordIn,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_set_password_tenant_user),
):
    """Establece la contraseña de un usuario de empresa del mismo tenant.

    Requiere rol de admin de empresa. No devuelve datos sensibles.
    """
    tenant_id = _tenant_empresa_id(request)
    update = UsuarioEmpresaUpdate(password=payload.password)
    services.actualizar_usuario_empresa(db, tenant_id, usuario_id, update)
    return {"ok": True}


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_usuario(
    request: Request,
    usuario_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_delete_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    services.toggle_usuario_activo(db, tenant_id, usuario_id, activo=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/modulos", response_model=list[ModuloOption])
def listar_modulos_empresa(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    return services.listar_modulos_empresa(db, tenant_id)


@router.get("/roles", response_model=list[RolEmpresaOption])
def listar_roles_empresa(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_perm_update_tenant_user),
):
    tenant_id = _tenant_empresa_id(request)
    return services.listar_roles_empresa(db, tenant_id)


@public_router.get("/check-username/{username}")
def check_username(username: str, db: Session = Depends(get_db)):
    disponible = services.check_username_availability(db, username)
    return {"available": disponible}
