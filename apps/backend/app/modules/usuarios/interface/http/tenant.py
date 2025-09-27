
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from typing import List

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

router = APIRouter(
    prefix="/tenant/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)

public_router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _tenant_empresa_id(request: Request) -> int:
    claims = request.state.access_claims
    empresa_id = claims.get("tenant_id")
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Empresa no encontrada en el token")
    return int(empresa_id)


@router.get("/", response_model=List[UsuarioEmpresaOut])
def listar_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    return services.listar_usuarios_empresa(db, empresa_id)


@router.post("/", response_model=UsuarioEmpresaOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    request: Request,
    usuario_in: UsuarioEmpresaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    return services.crear_usuario_empresa(
        db,
        empresa_id,
        usuario_in,
        asignado_por_id=getattr(current_user, "user_id", None),
    )


@router.patch("/{usuario_id}", response_model=UsuarioEmpresaOut)
def actualizar_usuario(
    request: Request,
    usuario_id: int,
    usuario_in: UsuarioEmpresaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    return services.actualizar_usuario_empresa(db, empresa_id, usuario_id, usuario_in)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_usuario(
    request: Request,
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    services.toggle_usuario_activo(db, empresa_id, usuario_id, activo=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/modulos", response_model=List[ModuloOption])
def listar_modulos_empresa(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    return services.listar_modulos_empresa(db, empresa_id)


@router.get("/roles", response_model=List[RolEmpresaOption])
def listar_roles_empresa(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(permissions.require_empresa_admin),
):
    empresa_id = _tenant_empresa_id(request)
    return services.listar_roles_empresa(db, empresa_id)


@public_router.get("/check-username/{username}")
def check_username(username: str, db: Session = Depends(get_db)):
    disponible = services.check_username_availability(db, username)
    return {"available": disponible}
