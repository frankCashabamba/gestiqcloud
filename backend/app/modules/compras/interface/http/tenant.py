from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import CompraRepo
from .schemas import CompraCreate, CompraUpdate, CompraOut

router = APIRouter()


@router.get("", response_model=list[CompraOut])
def list_compras(db: Session = Depends(get_db)):
    return CompraRepo(db).list()


@router.get("/{cid}", response_model=CompraOut)
def get_compra(cid: int, db: Session = Depends(get_db)):
    obj = CompraRepo(db).get(cid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=CompraOut)
def create_compra(payload: CompraCreate, db: Session = Depends(get_db)):
    return CompraRepo(db).create(**payload.model_dump())


@router.put("/{cid}", response_model=CompraOut)
def update_compra(cid: int, payload: CompraUpdate, db: Session = Depends(get_db)):
    try:
        return CompraRepo(db).update(cid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{cid}")
def delete_compra(cid: int, db: Session = Depends(get_db)):
    try:
        CompraRepo(db).delete(cid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
