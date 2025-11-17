"""Module: rolesempresas.py

Auto-generated module docstring."""

# routers/roles.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import RolEmpresa
from app.routers.protected import get_current_user
from app.schemas.configuracion import AuthenticatedUser
from app.settings.schemas.roles.roleempresas import RolCreate, RolEmpresaOut, RolResponse, RolUpdate

router = APIRouter(prefix="/api/roles", tags=["Roles"])


@router.get("", response_model=list[RolEmpresaOut])
def listar_roles(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    roles = db.query(RolEmpresa).filter_by(tenant_id=current_user.tenant_id).all()
    return roles


@router.post("")  # puedes poner response_model=RolResponse si tu schema coincide
def crear_rol(
    data: RolCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id

    existe = db.query(RolEmpresa).filter_by(tenant_id=tenant_id, nombre=data.name).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")

    nuevo_rol = RolEmpresa(
        tenant_id=tenant_id,
        nombre=data.name,
        descripcion=data.description,
        permisos=dict.fromkeys(data.permisos, True),
        rol_base_id=data.copiar_desde_id,
        creado_por_empresa=True,
    )

    db.add(nuevo_rol)
    db.commit()
    db.refresh(nuevo_rol)

    return {"message": "Rol creado correctamente", "id": nuevo_rol.id}


@router.put("/{rol_id}", response_model=RolResponse)
def update_rol(rol_id: int, rol: RolUpdate, db: Session = Depends(get_db)):
    """Function update_rol - auto-generated docstring."""
    db_rol = db.query(RolEmpresa).filter(RolEmpresa.id == rol_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    updates = rol.model_dump(exclude_unset=True, exclude_none=True)  # ← Pydantic v2
    # no permitir sobreescribir campos controlados por servidor
    updates.pop("id", None)
    updates.pop("tenant_id", None)

    for key, value in updates.items():
        setattr(db_rol, key, value)

    db.commit()
    db.refresh(db_rol)
    return {"message": "Rol actualizado", "id": db_rol.id}
