"""HR Lookup Service - Get configuration values from database"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.hr.lookups import (
    ContractType,
    DeductionType,
    DocumentIDType,
    EmployeeStatus,
    GenderType,
)


class HRLookupService:
    """Service for retrieving HR lookup values from database"""

    def __init__(self, db: Session):
        self.db = db

    def get_employee_statuses(self, tenant_id: UUID) -> list[dict]:
        """Get all active employee statuses for tenant"""
        rows = (
            self.db.query(EmployeeStatus)
            .filter(
                EmployeeStatus.tenant_id == tenant_id,
                EmployeeStatus.is_active,
            )
            .order_by(EmployeeStatus.sort_order)
            .all()
        )

        return [
            {
                "id": str(r.id),
                "code": r.code,
                "name_en": r.name_en,
                "name_es": r.name_es,
                "name_pt": r.name_pt,
                "color_code": r.color_code,
                "icon_code": r.icon_code,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]

    def get_contract_types(self, tenant_id: UUID) -> list[dict]:
        """Get all active contract types for tenant"""
        rows = (
            self.db.query(ContractType)
            .filter(
                ContractType.tenant_id == tenant_id,
                ContractType.is_active,
            )
            .order_by(ContractType.sort_order)
            .all()
        )

        return [
            {
                "id": str(r.id),
                "code": r.code,
                "name_en": r.name_en,
                "name_es": r.name_es,
                "name_pt": r.name_pt,
                "is_permanent": r.is_permanent,
                "full_time": r.full_time,
                "notice_period_days": r.notice_period_days,
                "probation_months": r.probation_months,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]

    def get_deduction_types(self, tenant_id: UUID) -> list[dict]:
        """Get all active deduction types for tenant"""
        rows = (
            self.db.query(DeductionType)
            .filter(
                DeductionType.tenant_id == tenant_id,
                DeductionType.is_active,
            )
            .order_by(DeductionType.sort_order)
            .all()
        )

        return [
            {
                "id": str(r.id),
                "code": r.code,
                "name_en": r.name_en,
                "name_es": r.name_es,
                "name_pt": r.name_pt,
                "is_deduction": r.is_deduction,
                "is_mandatory": r.is_mandatory,
                "is_percentage_based": r.is_percentage_based,
                "is_fixed_amount": r.is_fixed_amount,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]

    def get_gender_types(self, tenant_id: UUID) -> list[dict]:
        """Get all active gender types for tenant"""
        rows = (
            self.db.query(GenderType)
            .filter(
                GenderType.tenant_id == tenant_id,
                GenderType.is_active,
            )
            .order_by(GenderType.sort_order)
            .all()
        )

        return [
            {
                "id": str(r.id),
                "code": r.code,
                "name_en": r.name_en,
                "name_es": r.name_es,
                "name_pt": r.name_pt,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]

    def get_document_id_types(self, tenant_id: UUID, country_code: str | None = None) -> list[dict]:
        """Get all active document/ID types for tenant and country"""
        query = self.db.query(DocumentIDType).filter(
            DocumentIDType.tenant_id == tenant_id,
            DocumentIDType.is_active,
        )

        if country_code:
            query = query.filter(DocumentIDType.country_code == country_code)

        rows = query.order_by(DocumentIDType.sort_order).all()

        return [
            {
                "id": str(r.id),
                "country_code": r.country_code,
                "code": r.code,
                "name_en": r.name_en,
                "name_es": r.name_es,
                "name_pt": r.name_pt,
                "regex_pattern": r.regex_pattern,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]

    def get_document_id_type_by_code(
        self, tenant_id: UUID, code: str, country_code: str | None = None
    ) -> dict | None:
        """Get specific document ID type by code"""
        query = self.db.query(DocumentIDType).filter(
            DocumentIDType.tenant_id == tenant_id,
            DocumentIDType.code == code,
            DocumentIDType.is_active,
        )

        if country_code:
            query = query.filter(DocumentIDType.country_code == country_code)

        row = query.first()
        if not row:
            return None

        return {
            "id": str(row.id),
            "country_code": row.country_code,
            "code": row.code,
            "name_en": row.name_en,
            "name_es": row.name_es,
            "name_pt": row.name_pt,
            "regex_pattern": row.regex_pattern,
        }
