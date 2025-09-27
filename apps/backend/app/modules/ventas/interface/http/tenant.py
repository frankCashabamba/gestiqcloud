from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import VentaRepo
from .schemas import VentaCreate, VentaUpdate, VentaOut

router = APIRouter()


@router.get("", response_model=list[VentaOut])
def list_ventas(db: Session = Depends(get_db)):
    return VentaRepo(db).list()


@router.get("/{vid}", response_model=VentaOut)
def get_venta(vid: int, db: Session = Depends(get_db)):
    obj = VentaRepo(db).get(vid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=VentaOut)
def create_venta(payload: VentaCreate, db: Session = Depends(get_db)):
    return VentaRepo(db).create(**payload.model_dump())


@router.put("/{vid}", response_model=VentaOut)
def update_venta(vid: int, payload: VentaUpdate, db: Session = Depends(get_db)):
    try:
        return VentaRepo(db).update(vid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{vid}")
def delete_venta(vid: int, db: Session = Depends(get_db)):
    try:
        VentaRepo(db).delete(vid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
