"""Module: rolesempresas.py

Auto-generated module docstring."""

# routers/roles.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import RolEmpresa
from app.routers.protected import get_current_user
from app.schemas.configuracion import AuthenticatedUser
from app.settings.schemas.roles.roleempresas import (RolCreate, RolEmpresaOut,
                                                     RolResponse, RolUpdate)

router = APIRouter(prefix="/api/roles", tags=["Roles"])


@router.get("", response_model=List[RolEmpresaOut])
def listar_roles(   
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    roles = db.query(RolEmpresa).filter_by(empresa_id=current_user.empresa_id).all()
    return roles

@router.post("")
def crear_rol(
   
    data: RolCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    empresa_id = current_user.empresa_id

    existe = db.query(RolEmpresa).filter_by(empresa_id=empresa_id, nombre=data.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")

    nuevo_rol = RolEmpresa(
        empresa_id=empresa_id,
        nombre=data.nombre,
        descripcion=data.descripcion,
        permisos={perm: True for perm in data.permisos},
        rol_base_id=data.copiar_desde_id,
        creado_por_empresa=True
    )

    db.add(nuevo_rol)
    db.commit()
    db.refresh(nuevo_rol)

    return {"message": "Rol creado correctamente", "id": nuevo_rol.id}

@router.put("/{rol_id}", response_model=RolResponse)
def update_rol(rol_id: int, rol: RolUpdate, db: Session = Depends(get_db)):
    """ Function update_rol - auto-generated docstring. """
    db_rol = db.query(RolEmpresa).filter(RolEmpresa.id == rol_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    for key, value in rol.dict().items():
        setattr(db_rol, key, value)

    db.commit()
    db.refresh(db_rol)
    return db_rol
