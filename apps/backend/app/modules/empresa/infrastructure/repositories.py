from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from app.models.tenant import Tenant as CompanyORM
from app.modules.empresa.application.ports import CompanyDTO, CompanyRepo
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo

logger = logging.getLogger(__name__)


def _to_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class SqlCompanyRepo(SqlAlchemyRepo, CompanyRepo):
    def _to_dto(self, e: CompanyORM) -> CompanyDTO:
        return CompanyDTO(
            id=getattr(e, "id", None),
            name=getattr(e, "name", None),
            slug=getattr(e, "slug", None),
        )

    def list_all(self) -> Sequence[CompanyDTO]:
        logger.debug("DB URL: %s", str(self.db.get_bind().url))
        rows = self.db.query(CompanyORM).order_by(CompanyORM.id.desc()).limit(200).all()
        logger.debug("Companies found: %d", len(rows))
        return [self._to_dto(e) for e in rows]

    def list_by_tenant(self, *, tenant_id: Any) -> Sequence[CompanyDTO]:
        tenant_uuid = _to_uuid(tenant_id)
        rows = (
            self.db.query(CompanyORM)
            .filter(CompanyORM.id == tenant_uuid)
            .order_by(CompanyORM.id.desc())
            .all()
        )
        return [self._to_dto(e) for e in rows]

    def get(self, *, id: Any) -> CompanyDTO | None:
        e = self.db.query(CompanyORM).filter(CompanyORM.id == _to_uuid(id)).first()
        return self._to_dto(e) if e else None

    # --- CRUD admin ---
    def create(self, data: Mapping) -> CompanyDTO:
        m = CompanyORM(
            name=data.get("name"),
            slug=data.get("slug"),
            tax_id=data.get("tax_id"),
            phone=data.get("phone"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            postal_code=data.get("cp"),
            country=data.get("country"),
            logo=data.get("logo"),
            primary_color=data.get("primary_color") or "#4f46e5",
            active=bool(data.get("active", True)),
            deactivation_reason=data.get("deactivation_reason"),
            default_template=data.get("initial_template") or "client",
            website=data.get("website"),
            config_json=data.get("config_json"),
        )
        self.db.add(m)
        # No commit here: allow caller to wrap company+admin user in a single transaction
        # Flush to obtain PK and keep atomicity at endpoint level
        self.db.flush()
        self.db.refresh(m)
        return self._to_dto(m)

    def update(self, id: Any, data: Mapping) -> CompanyDTO | None:
        m = self.db.query(CompanyORM).filter(CompanyORM.id == _to_uuid(id)).first()
        if not m:
            return None
        for field in (
            "name",
            "slug",
            "tax_id",
            "phone",
            "address",
            "city",
            "state",
            "postal_code",
            "country",
            "logo",
            "primary_color",
            "active",
            "deactivation_reason",
            "default_template",
            "website",
            "config_json",
        ):
            if field in data and data[field] is not None:
                setattr(m, field, data[field])
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_dto(m)

    def delete(self, id: Any) -> bool:
        m = self.db.query(CompanyORM).filter(CompanyORM.id == _to_uuid(id)).first()
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        return True
