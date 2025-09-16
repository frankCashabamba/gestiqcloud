"""Module: categorias.py

Auto-generated module docstring."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import CategoriaEmpresa as CategoriaModel
from app.schemas.configuracion import CategoriaEmpresa, CategoriaEmpresaCreate

router = APIRouter(prefix="/api/categorias-empresa", tags=["categorias"])

@router.get("/", response_model=List[CategoriaEmpresa])
def list_categorias(db: Session = Depends(get_db)):
    """ Function list_categorias - auto-generated docstring. """
    return db.query(CategoriaModel).all()

@router.post("/", response_model=CategoriaEmpresa)
def create_categoria(data: CategoriaEmpresaCreate, db: Session = Depends(get_db)):
    """ Function create_categoria - auto-generated docstring. """
    nueva = CategoriaModel(**data.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/{id}", response_model=CategoriaEmpresa)
def update_categoria(id: int, data: CategoriaEmpresaCreate, db: Session = Depends(get_db)):
    """ Function update_categoria - auto-generated docstring. """
    cat = db.query(CategoriaModel).get(id)
    if not cat:
        raise HTTPException(status_code=404)
    for k, v in data.dict().items():
        setattr(cat, k, v)
    db.commit()
    return cat

@router.delete("/{id}")
def delete_categoria(id: int, db: Session = Depends(get_db)):
    """ Function delete_categoria - auto-generated docstring. """
    cat = db.query(CategoriaModel).get(id)
    if not cat:
        raise HTTPException(status_code=404)
    db.delete(cat)
    db.commit()
    return {"detail": "Eliminado"}
