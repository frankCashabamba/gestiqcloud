"""HR Lookup Endpoints - Public API for configuration values"""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.country_catalogs import CountryIdType
from app.models.hr.lookups import DocumentIDType
from app.modules.hr.services.lookup_service import HRLookupService

router = APIRouter(prefix="/hr", tags=["HR Lookups"])

# Tipos de documento estándar por país (lazy-seed cuando la tabla está vacía)
_SEED_ID_TYPES: dict[str, list[dict]] = {
    "EC": [
        {
            "code": "CEDULA",
            "name_en": "Identity Card",
            "name_es": "Cédula de identidad",
            "regex_pattern": r"^\d{10}$",
            "sort_order": 1,
        },
        {
            "code": "RUC",
            "name_en": "Tax ID (RUC)",
            "name_es": "RUC",
            "regex_pattern": r"^\d{13}$",
            "sort_order": 2,
        },
        {
            "code": "PASSPORT",
            "name_en": "Passport",
            "name_es": "Pasaporte",
            "regex_pattern": None,
            "sort_order": 3,
        },
    ],
    "ES": [
        {
            "code": "DNI",
            "name_en": "National ID",
            "name_es": "DNI",
            "regex_pattern": r"^\d{8}[A-Z]$",
            "sort_order": 1,
        },
        {
            "code": "NIE",
            "name_en": "Foreigner ID",
            "name_es": "NIE",
            "regex_pattern": r"^[XYZ]\d{7}[A-Z]$",
            "sort_order": 2,
        },
        {
            "code": "PASSPORT",
            "name_en": "Passport",
            "name_es": "Pasaporte",
            "regex_pattern": None,
            "sort_order": 3,
        },
    ],
}


def _seed_id_types_for_tenant(db: Session, tenant_id: UUID, country_code: str) -> None:
    """Inserta los tipos de documento para un tenant leyendo del catálogo global CountryIdType.
    Si no hay entradas globales para el país, usa los valores hardcodeados como fallback.
    """
    cc = country_code.upper()
    global_types = (
        db.query(CountryIdType)
        .filter(CountryIdType.country_code == cc, CountryIdType.active.is_(True))
        .order_by(CountryIdType.code)
        .all()
    )

    # Fallback: si no hay catálogo global, usar valores hardcodeados
    if not global_types:
        templates = _SEED_ID_TYPES.get(cc, _SEED_ID_TYPES["EC"])
    else:
        templates = [
            {
                "code": g.code,
                "name_en": g.label,
                "name_es": g.label,
                "regex_pattern": None,
                "sort_order": idx + 1,
            }
            for idx, g in enumerate(global_types)
        ]

    for t in templates:
        exists = (
            db.query(DocumentIDType)
            .filter_by(tenant_id=tenant_id, country_code=cc, code=t["code"])
            .first()
        )
        if not exists:
            db.add(
                DocumentIDType(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    country_code=cc,
                    code=t["code"],
                    name_en=t["name_en"],
                    name_es=t["name_es"],
                    regex_pattern=t["regex_pattern"],
                    sort_order=t["sort_order"],
                    is_active=True,
                )
            )
    db.commit()


@router.get("/statuses")
async def get_employee_statuses(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
):
    """Get all employee statuses for tenant"""
    service = HRLookupService(db)
    statuses = service.get_employee_statuses(tenant_id)
    return {"data": statuses}


@router.get("/contract-types")
async def get_contract_types(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
):
    """Get all contract types for tenant"""
    service = HRLookupService(db)
    contracts = service.get_contract_types(tenant_id)
    return {"data": contracts}


@router.get("/deduction-types")
async def get_deduction_types(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
):
    """Get all deduction types for tenant"""
    service = HRLookupService(db)
    deductions = service.get_deduction_types(tenant_id)
    return {"data": deductions}


@router.get("/gender-types")
async def get_gender_types(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
):
    """Get all gender types for tenant"""
    service = HRLookupService(db)
    genders = service.get_gender_types(tenant_id)
    return {"data": genders}


@router.get("/document-id-types")
async def get_document_id_types(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
    country_code: str | None = None,
):
    """Get all document/ID types for tenant (optionally filtered by country).
    Auto-seeds standard types for the country if the table is empty.
    """
    service = HRLookupService(db)
    id_types = service.get_document_id_types(tenant_id, country_code)
    if not id_types:
        # Lazy-seed: insertar tipos estándar para el país (EC por defecto)
        _seed_id_types_for_tenant(db, tenant_id, country_code or "EC")
        id_types = service.get_document_id_types(tenant_id, country_code)
    return {"data": id_types}


@router.get("/document-id-types/{code}")
async def get_document_id_type_by_code(
    code: str,
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...),
    country_code: str | None = None,
):
    """Get specific document/ID type by code"""
    service = HRLookupService(db)
    id_type = service.get_document_id_type_by_code(tenant_id, code, country_code)
    if not id_type:
        return {"data": None, "error": f"Document ID type '{code}' not found"}
    return {"data": id_type}
