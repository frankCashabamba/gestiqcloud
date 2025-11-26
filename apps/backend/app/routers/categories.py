"""Module: categories.py

Auto-generated module docstring."""

from app.config.database import get_db
from app.models import CategoriaEmpresa as CategoryModel
from app.schemas.configuracion import CategoriaEmpresa as CompanyCategory
from app.schemas.configuracion import CategoriaEmpresaCreate as CompanyCategoryCreate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Old URL: /api/categorias-empresa (deprecated, use new endpoint for backward compatibility if needed)
router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("/", response_model=list[CompanyCategory])
def list_categories(db: Session = Depends(get_db)):
    """Function list_categories - auto-generated docstring."""
    return db.query(CategoryModel).all()


@router.post("/", response_model=CompanyCategory)
def create_category(data: CompanyCategoryCreate, db: Session = Depends(get_db)):
    """Function create_category - auto-generated docstring."""
    payload = data.model_dump(exclude_none=True)
    nueva = CategoryModel(**payload)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/{id}", response_model=CompanyCategory)
def update_category(id: int, data: CompanyCategoryCreate, db: Session = Depends(get_db)):
    """Function update_category - auto-generated docstring."""
    cat = db.get(CategoryModel, id)  # avoid query().get() (legacy)
    if not cat:
        raise HTTPException(status_code=404)

    updates = data.model_dump(exclude_unset=True, exclude_none=True)  # only provided fields
    for k, v in updates.items():
        setattr(cat, k, v)

    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{id}")
def delete_category(id: int, db: Session = Depends(get_db)):
    """Function delete_category - auto-generated docstring."""
    cat = db.get(CategoryModel, id)
    if not cat:
        raise HTTPException(status_code=404)
    db.delete(cat)
    db.commit()
    return {"detail": "Deleted"}
