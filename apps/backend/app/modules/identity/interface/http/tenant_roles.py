"""Router for tenant (company) role management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.company.company_role import CompanyRole as CompanyRole
from app.models.company.tenant import Empresa
from app.schemas.company_role import CompanyRoleCreate, CompanyRoleOut, CompanyRoleUpdate

router = APIRouter(
    prefix="/tenant/roles",
    tags=["tenant-roles"],
    dependencies=[
        Depends(with_access_claims),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[CompanyRoleOut])
async def list_roles(
    db: Session = Depends(get_db),
    claims: dict = Depends(require_scope("tenant")),
):
    """List all roles for the current tenant."""
    empresa = db.execute(
        select(Empresa).where(Empresa.id == claims.get("tenant_id"))
    ).scalar_one_or_none()

    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    roles = (
        db.execute(
            select(CompanyRole)
            .where(CompanyRole.tenant_id == empresa.id)
            .order_by(CompanyRole.name)
        )
        .scalars()
        .all()
    )

    return roles


@router.get("/{role_id}", response_model=CompanyRoleOut)
async def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    _claims: dict = Depends(require_scope("tenant")),
):
    """Get a role by ID."""
    role = db.get(CompanyRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return role


@router.post("", response_model=CompanyRoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: CompanyRoleCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_scope("tenant")),
):
    """Create a new role for the current tenant."""
    if not claims.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create roles",
        )

    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User company not found",
        )

    existing = db.execute(
        select(CompanyRole).where(
            CompanyRole.tenant_id == tenant_id, CompanyRole.name == payload.name
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A role with the name '{payload.name}' already exists",
        )

    new_role = CompanyRole(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        permissions=payload.permissions or {},
        created_by_company=True,
    )

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return new_role


@router.patch("/{role_id}", response_model=CompanyRoleOut)
async def update_role(
    role_id: UUID,
    payload: CompanyRoleUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_scope("tenant")),
):
    """Update an existing role."""
    if not claims.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can modify roles",
        )

    role = db.get(CompanyRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = db.execute(
            select(CompanyRole).where(
                CompanyRole.tenant_id == role.tenant_id,
                CompanyRole.name == update_data["name"],
                CompanyRole.id != role_id,
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A role with the name '{update_data['name']}' already exists",
            )

    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)

    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_scope("tenant")),
):
    """Delete a role."""
    if not claims.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete roles",
        )

    role = db.get(CompanyRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    from app.models.company.company_user_role import CompanyUserRole

    users_with_role = db.execute(
        select(CompanyUserRole).where(CompanyUserRole.role_id == role_id).limit(1)
    ).scalar_one_or_none()

    if users_with_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete role because there are users assigned to it",
        )

    db.delete(role)
    db.commit()

    return None
