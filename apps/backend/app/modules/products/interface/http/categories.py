"""Module: categories.py

DEPRECATED: This router is deprecated. Use /api/v1/business-categories/ instead.
"""

import warnings

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import CompanyCategory as CategoryModel
from app.schemas.configuracion import CompanyCategory, CompanyCategoryCreate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("/", response_model=list[CompanyCategory], deprecated=True)
def list_categories(db: Session = Depends(get_db)):
    """
    DEPRECATED: Use GET /api/v1/business-categories/ instead.

    This endpoint will be removed in Q1 2026.
    """
    warnings.warn(
        "GET /api/v1/categories/ is deprecated. Use /api/v1/business-categories/ instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return db.query(CategoryModel).all()


@router.post("/", response_model=CompanyCategory, deprecated=True)
def create_category(data: CompanyCategoryCreate, db: Session = Depends(get_db)):
    """
    DEPRECATED: Use POST /api/v1/business-categories/ instead.

    This endpoint will be removed in Q1 2026.
    """
    warnings.warn(
        "POST /api/v1/categories/ is deprecated. Use /api/v1/business-categories/ instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    payload = data.model_dump(exclude_none=True)
    new_category = CategoryModel(**payload)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{id}", response_model=CompanyCategory, deprecated=True)
def update_category(id: int, data: CompanyCategoryCreate, db: Session = Depends(get_db)):
    """
    DEPRECATED: Use PUT /api/v1/business-categories/{id} instead.

    This endpoint will be removed in Q1 2026.
    """
    warnings.warn(
        "PUT /api/v1/categories/{id} is deprecated. Use /api/v1/business-categories/ instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    cat = db.get(CategoryModel, id)
    if not cat:
        raise HTTPException(status_code=404)

    updates = data.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in updates.items():
        setattr(cat, k, v)

    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{id}", deprecated=True)
def delete_category(id: int, db: Session = Depends(get_db)):
    """
    DEPRECATED: Use DELETE /api/v1/business-categories/{id} instead.

    This endpoint will be removed in Q1 2026.
    """
    warnings.warn(
        "DELETE /api/v1/categories/{id} is deprecated. Use /api/v1/business-categories/ instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    cat = db.get(CategoryModel, id)
    if not cat:
        raise HTTPException(status_code=404)
    db.delete(cat)
    db.commit()
    return {"detail": "Deleted"}
