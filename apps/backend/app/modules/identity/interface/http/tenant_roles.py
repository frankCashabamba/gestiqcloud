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
from app.schemas.company_role import (
    CompanyRoleCreate,
    CompanyRoleOut,
    CompanyRoleSeedEntry,
    CompanyRoleSeedSummary,
    CompanyRoleUpdate,
)

router = APIRouter(
    prefix="/tenant/roles",
    tags=["tenant-roles"],
    dependencies=[
        Depends(with_access_claims),
        Depends(ensure_rls),
    ],
)


def _normalize_sector_slug(raw: str | None) -> str | None:
    value = (raw or "").strip().lower()
    if not value:
        return None
    if value in {"panerp", "panaderia"}:
        return "panaderia"
    return value


def _operational_role_presets(sector: str | None) -> list[dict]:
    cashier_name = "Cajera" if sector == "panaderia" else "Caja"
    operator_name = "Panadero" if sector == "panaderia" else "Operario"

    return [
        {
            "name": cashier_name,
            "description": "Operacion de caja y ventas de mostrador",
            "permissions": {
                "pos": {"read": True, "create": True, "update": True},
            },
        },
        {
            "name": operator_name,
            "description": "Operacion diaria de produccion y consulta de stock",
            "permissions": {
                "produccion": {"read": True, "write": True},
                "inventory": {"read": True},
                "products": {"read": True},
            },
        },
        {
            "name": "Encargado",
            "description": "Supervision operativa de caja, stock, produccion y RRHH basico",
            "permissions": {
                "pos": {"read": True, "create": True, "update": True},
                "inventory": {"read": True, "create": True, "update": True},
                "produccion": {"read": True, "write": True},
                "hr": {"read": True, "manage": True},
                "reportes": {"read": True},
            },
        },
    ]


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


@router.post("/seed-operational", response_model=CompanyRoleSeedSummary)
async def seed_operational_roles(
    db: Session = Depends(get_db),
    claims: dict = Depends(require_scope("tenant")),
):
    """Create a minimal operational role set for the current tenant."""
    if not claims.get("is_company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can seed operational roles",
        )

    empresa = db.execute(
        select(Empresa).where(Empresa.id == claims.get("tenant_id"))
    ).scalar_one_or_none()

    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    sector = _normalize_sector_slug(getattr(empresa, "sector_template_name", None))
    presets = _operational_role_presets(sector)

    created = 0
    existing = 0
    seeded_roles: list[tuple[CompanyRole, str]] = []

    for preset in presets:
        role = db.execute(
            select(CompanyRole).where(
                CompanyRole.tenant_id == empresa.id,
                CompanyRole.name == preset["name"],
            )
        ).scalar_one_or_none()

        if role is None:
            role = CompanyRole(
                tenant_id=empresa.id,
                name=preset["name"],
                description=preset["description"],
                permissions=preset["permissions"],
                created_by_company=True,
            )
            db.add(role)
            db.flush()
            created += 1
            seeded_roles.append((role, "created"))
            continue

        existing += 1
        seeded_roles.append((role, "existing"))

    db.commit()
    items: list[CompanyRoleSeedEntry] = []
    for role, item_status in seeded_roles:
        db.refresh(role)
        items.append(CompanyRoleSeedEntry(role=role, status=item_status))

    return CompanyRoleSeedSummary(
        template="operational",
        sector=sector,
        created=created,
        existing=existing,
        items=items,
    )


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
