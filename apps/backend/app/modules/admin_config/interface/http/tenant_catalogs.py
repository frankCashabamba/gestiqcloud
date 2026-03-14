"""Read-only endpoints for tenant frontend to consume global catalogs.

These replace hardcoded dropdown values in the tenant UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.country_catalogs import CountryTaxCode
from app.models.core.global_catalogs import (
    DocumentType,
    ExpenseCategoryGlobal,
    PaymentMethodTemplate,
    UnitOfMeasure,
)
from app.services.unit_catalog_service import normalize_operational_unit

router = APIRouter(prefix="/catalogs", tags=["tenant:catalogs"])


@router.get("/tax-types")
def list_tax_types(country_code: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CountryTaxCode).filter(CountryTaxCode.active.is_(True))
    if country_code:
        q = q.filter(CountryTaxCode.country_code == country_code.upper())
    rows = q.order_by(CountryTaxCode.code).all()
    return [
        {
            "id": str(r.id),
            "country_code": r.country_code,
            "code": r.code,
            "name": r.name,
            "rate_default": float(r.rate_default) if r.rate_default is not None else None,
        }
        for r in rows
    ]


@router.get("/units")
def list_units(db: Session = Depends(get_db)):
    rows = (
        db.query(UnitOfMeasure)
        .filter(UnitOfMeasure.active.is_(True))
        .order_by(UnitOfMeasure.code)
        .all()
    )
    return [
        {
            "id": r.id,
            "code": normalize_operational_unit(r.abbreviation or r.code),
            "catalog_code": r.code,
            "name": r.name,
            "label": r.name,
            "abbreviation": r.abbreviation,
        }
        for r in rows
    ]


@router.get("/doc-types")
def list_doc_types(db: Session = Depends(get_db)):
    rows = (
        db.query(DocumentType)
        .filter(DocumentType.active.is_(True))
        .order_by(DocumentType.code)
        .all()
    )
    return [
        {"id": r.id, "code": r.code, "name": r.name, "description": r.description} for r in rows
    ]


@router.get("/expense-categories")
def list_expense_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(ExpenseCategoryGlobal)
        .filter(ExpenseCategoryGlobal.active.is_(True))
        .order_by(ExpenseCategoryGlobal.code)
        .all()
    )
    return [
        {"id": r.id, "code": r.code, "name": r.name, "parent_code": r.parent_code} for r in rows
    ]


@router.get("/payment-methods")
def list_payment_methods(db: Session = Depends(get_db)):
    rows = (
        db.query(PaymentMethodTemplate)
        .filter(PaymentMethodTemplate.active.is_(True))
        .order_by(PaymentMethodTemplate.code)
        .all()
    )
    return [
        {"id": r.id, "code": r.code, "name": r.name, "description": r.description} for r in rows
    ]


@router.get("/countries")
def list_countries(db: Session = Depends(get_db)):
    from app.models.company.company import Country

    rows = db.query(Country).filter(Country.active.is_(True)).order_by(Country.code).all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]
