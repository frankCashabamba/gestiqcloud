from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import GastoRepo
from .schemas import GastoCreate, GastoUpdate, GastoOut

router = APIRouter(prefix="/gastos")


@router.get("", response_model=list[GastoOut])
def list_gastos(db: Session = Depends(get_db)):
    return GastoRepo(db).list()


@router.get("/{gid}", response_model=GastoOut)
def get_gasto(gid: int, db: Session = Depends(get_db)):
    obj = GastoRepo(db).get(gid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=GastoOut)
def create_gasto(payload: GastoCreate, db: Session = Depends(get_db)):
    return GastoRepo(db).create(**payload.model_dump())


@router.put("/{gid}", response_model=GastoOut)
def update_gasto(gid: int, payload: GastoUpdate, db: Session = Depends(get_db)):
    try:
        return GastoRepo(db).update(gid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{gid}")
def delete_gasto(gid: int, db: Session = Depends(get_db)):
    try:
        GastoRepo(db).delete(gid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
