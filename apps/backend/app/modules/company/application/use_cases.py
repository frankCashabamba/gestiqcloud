from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.company.company_user import CompanyUser
from app.modules.company.application.ports import CompanyDTO, CompanyRepo
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.shared.application.base import BaseUseCase


class ListCompaniesAdmin(BaseUseCase[CompanyRepo]):
    def execute(self) -> Sequence[CompanyDTO]:
        return list(self.repo.list_all())


class ListCompaniesTenant(BaseUseCase[CompanyRepo]):
    def execute(self, *, tenant_id: uuid.UUID | str) -> Sequence[CompanyDTO]:
        return list(self.repo.list_by_tenant(tenant_id=tenant_id))


# ----------------------------
# Use-case helper: create company admin user
# ----------------------------
def create_company_admin_user(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    password: str,
) -> CompanyUser:
    """
    Create a CompanyUser with admin role (is_company_admin=True),
    validating email/username uniqueness (lowercase). Does not commit.
    Raises ValueError('user_email_or_username_taken') on collision.
    """
    email_clean = (email or "").strip().lower()
    username_clean = (username or "").strip().lower()

    exists = (
        db.query(CompanyUser)
        .filter(
            (func.lower(CompanyUser.email) == email_clean)
            | (func.lower(CompanyUser.username) == username_clean)
        )
        .first()
    )
    if exists:
        raise ValueError("user_email_or_username_taken")

    hasher = PasslibPasswordHasher()
    user = CompanyUser(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        email=email_clean,
        username=username_clean,
        password_hash=hasher.hash(password),
        is_company_admin=True,
        is_active=True,
    )
    db.add(user)
    return user
