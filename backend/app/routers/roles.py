"""Module: roles.py

Auto-generated module docstring."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import PermisoAccionGlobal
from app.models import RolBase as RolModel
from app.schemas.configuracion import (PermisoAccionGlobalpermiso, RolBase,
                                       RolBaseCreate, RolBaseUpdate)

from .protected import get_current_user

router = APIRouter(prefix="/roles-base", tags=["roles"] ,
    dependencies=[Depends(get_current_user)])

@router.get("/", response_model=List[RolBase])
def list_roles(db: Session = Depends(get_db)):
    """ Function list_roles - auto-generated docstring. """
    return db.query(RolModel).all()

@router.post("/", response_model=RolBase)
def create_rol(data: RolBaseCreate, db: Session = Depends(get_db)):
    """ Function create_rol - auto-generated docstring. """
    print("Datos recibidos:", data.dict())

    if not all(isinstance(p, str) for p in data.permisos):
        print("❌ Permisos inválidos en POST:", data.permisos)
        raise HTTPException(status_code=400, detail="Todos los permisos deben ser strings")

    nuevo = RolModel(**data.dict())
    db.add(nuevo)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print("Error al guardar:", e)
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre.")
    except Exception as e:
        db.rollback()
        print("Error desconocido:", e)
        raise HTTPException(status_code=400, detail=str(e))

    db.refresh(nuevo)
    print("Nuevo antes del return:", nuevo.permisos)
    return nuevo

@router.put("/{id}", response_model=RolBase)
def update_rol(id: int, data: RolBaseUpdate, db: Session = Depends(get_db)):
    """ Function update_rol - auto-generated docstring. """
    if not all(isinstance(p, str) for p in data.permisos):
        raise HTTPException(status_code=400, detail="Todos los permisos deben ser strings")

    rol = db.query(RolModel).get(id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    existe = db.query(RolModel).filter(RolModel.nombre == data.nombre, RolModel.id != id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre.")

    rol.nombre = data.nombre
    rol.descripcion = data.descripcion
    rol.permisos = data.permisos
    db.commit()
    db.refresh(rol)  
    return rol


@router.delete("/{id}", response_model=dict)
def delete_rol(id: int, db: Session = Depends(get_db)):
    """ Function delete_rol - auto-generated docstring. """
    rol = db.query(RolModel).get(id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    db.delete(rol)
    db.commit()
    return {"detail": "Eliminado"}

@router.get("/permisos-globales", response_model=List[PermisoAccionGlobalpermiso])
def list_permisos(db: Session = Depends(get_db)):
    """ Function list_permisos - auto-generated docstring. """
    return db.query(PermisoAccionGlobal).all()
