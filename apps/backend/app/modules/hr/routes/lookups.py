"""HR Lookup Endpoints - Public API for configuration values"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.modules.hr.services.lookup_service import HRLookupService

router = APIRouter(prefix="/hr", tags=["HR Lookups"])


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
    """Get all document/ID types for tenant (optionally filtered by country)"""
    service = HRLookupService(db)
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
