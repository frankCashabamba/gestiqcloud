"""Router para gestión de roles de empresa (tenant)."""

from app.config.database import get_db
from app.core.deps import require_tenant as require_current_user
from app.db.rls import ensure_rls
from app.models.company.company_role import CompanyRole as CompanyRole
from app.models.company.tenant import Empresa
from app.schemas.rol_empresa import RolEmpresaCreate, RolEmpresaOut, RolEmpresaUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tenant/roles", tags=["tenant-roles"])


@router.get("", response_model=list[RolEmpresaOut])
async def list_roles(db: Session = Depends(get_db), current_user=Depends(require_current_user)):
    """Listar todos los roles del tenant actual."""
    ensure_rls(db, current_user.get("tenant_id"))

    # Obtener tenant_id del tenant
    empresa = db.execute(
        select(Empresa).where(Empresa.id == current_user.get("tenant_id"))
    ).scalar_one_or_none()

    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")

    roles = (
        db.execute(
            select(CompanyRole)
            .where(CompanyRole.tenant_id == empresa.id)
            .order_by(CompanyRole.name)
        )
        .scalars()
        .all()
    )

    return roles


@router.get("/{rol_id}", response_model=RolEmpresaOut)
async def get_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_current_user),
):
    """Obtener un rol por ID."""
    ensure_rls(db, current_user.get("tenant_id"))

    rol = db.get(CompanyRole, rol_id)
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    return rol


@router.post("", response_model=RolEmpresaOut, status_code=status.HTTP_201_CREATED)
async def create_rol(
    payload: RolEmpresaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_current_user),
):
    """Crear un nuevo rol para el tenant actual."""
    ensure_rls(db, current_user.get("tenant_id"))

    # Verify admin
    if not current_user.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear roles",
        )

    # Obtener tenant_id
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontró la empresa del usuario",
        )

    # Verificar que no exista un rol con el mismo nombre
    existing = db.execute(
        select(CompanyRole).where(
            CompanyRole.tenant_id == tenant_id, CompanyRole.name == payload.name
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un rol con el nombre '{payload.name}'",
        )

    # Crear rol
    nuevo_rol = CompanyRole(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        permissions=payload.permisos or {},
        created_by_company=True,
    )

    db.add(nuevo_rol)
    db.commit()
    db.refresh(nuevo_rol)

    return nuevo_rol


@router.patch("/{rol_id}", response_model=RolEmpresaOut)
async def update_rol(
    rol_id: int,
    payload: RolEmpresaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_current_user),
):
    """Actualizar un rol existente."""
    ensure_rls(db, current_user.get("tenant_id"))

    # Verify admin
    if not current_user.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden modificar roles",
        )

    rol = db.get(CompanyRole, rol_id)
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    # Actualizar campos
    update_data = payload.model_dump(exclude_unset=True)

    # Si se actualiza el nombre, verificar unicidad
    if "name" in update_data:
        existing = db.execute(
            select(CompanyRole).where(
                CompanyRole.tenant_id == rol.tenant_id,
                CompanyRole.name == update_data["name"],
                CompanyRole.id != rol_id,
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un rol con el nombre '{update_data['name']}'",
            )

    for field, value in update_data.items():
        setattr(rol, field, value)

    db.commit()
    db.refresh(rol)

    return rol


@router.delete("/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_current_user),
):
    """Eliminar un rol."""
    ensure_rls(db, current_user.get("tenant_id"))

    # Verificar que es admin
    if not current_user.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden eliminar roles",
        )

    rol = db.get(CompanyRole, rol_id)
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    # Verificar que el rol no esté en uso
    from app.models.usuarios.usuario_rol_empresa import CompanyUserRole

    usuarios_con_rol = db.execute(
        select(CompanyUserRole).where(CompanyUserRole.rol_id == rol_id).limit(1)
    ).scalar_one_or_none()

    if usuarios_con_rol:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el rol porque hay usuarios asignados a él",
        )

    db.delete(rol)
    db.commit()

    return None
