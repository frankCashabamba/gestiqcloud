from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import ProveedorRepo
from .schemas import ProveedorCreate, ProveedorUpdate, ProveedorOut

router = APIRouter()


@router.get("", response_model=list[ProveedorOut])
def list_proveedores(db: Session = Depends(get_db)):
    return ProveedorRepo(db).list()


@router.get("/{pid}", response_model=ProveedorOut)
def get_proveedor(pid: int, db: Session = Depends(get_db)):
    obj = ProveedorRepo(db).get(pid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=ProveedorOut)
def create_proveedor(payload: ProveedorCreate, db: Session = Depends(get_db)):
    return ProveedorRepo(db).create(**payload.model_dump())


@router.put("/{pid}", response_model=ProveedorOut)
def update_proveedor(pid: int, payload: ProveedorUpdate, db: Session = Depends(get_db)):
    try:
        return ProveedorRepo(db).update(pid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{pid}")
def delete_proveedor(pid: int, db: Session = Depends(get_db)):
    try:
        ProveedorRepo(db).delete(pid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
