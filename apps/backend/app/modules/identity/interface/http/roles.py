"""Roles and global permissions management router."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import GlobalActionPermission
from app.models import RolBase as RolModel
from app.routers.protected import get_current_user
from app.schemas.configuracion import (
    GlobalActionPermissionCreate,
    GlobalActionPermissionSchema,
    GlobalActionPermissionUpdate,
    RolBase,
    RolBaseCreate,
    RolBaseUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/roles-base",
    tags=["roles"],
    dependencies=[Depends(get_current_user)],
)


def _require_admin(current_user):
    """Check that the current user is an admin or superadmin."""
    if getattr(current_user, "is_superadmin", False):
        return
    if getattr(current_user, "user_type", None) != "admin":
        raise HTTPException(status_code=403, detail="admin_only")


@router.get("/", response_model=list[RolBase])
def list_roles(db: Session = Depends(get_db)):
    """List all roles."""
    return db.query(RolModel).all()


@router.post("/", response_model=RolBase)
def create_role(data: RolBaseCreate, db: Session = Depends(get_db)):
    """Create a new role."""
    if not all(isinstance(p, str) for p in data.permissions):
        raise HTTPException(status_code=400, detail="All permissions must be strings")

    payload = data.model_dump(exclude_none=True)
    new_role = RolModel(**payload)
    db.add(new_role)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A role with that name already exists.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    db.refresh(new_role)
    return new_role


@router.put("/{id}", response_model=RolBase)
def update_role(id: int, data: RolBaseUpdate, db: Session = Depends(get_db)):
    """Update an existing role."""
    role = db.get(RolModel, id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    updates = data.model_dump(exclude_unset=True)

    if "permissions" in updates:
        permissions = updates["permissions"] or []
        if not all(isinstance(p, str) for p in permissions):
            raise HTTPException(status_code=400, detail="All permissions must be strings")

    new_name: str | None = updates.get("name")
    if new_name and new_name != role.name:
        existing = db.query(RolModel).filter(RolModel.name == new_name, RolModel.id != id).first()
        if existing:
            raise HTTPException(status_code=400, detail="A role with that name already exists.")

    for k, v in updates.items():
        setattr(role, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A role with that name already exists.")
    db.refresh(role)
    return role


@router.delete("/{id}", response_model=dict)
def delete_role(id: int, db: Session = Depends(get_db)):
    """Delete a role by ID."""
    role = db.get(RolModel, id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"detail": "Deleted"}


@router.get("/global-permissions", response_model=list[GlobalActionPermissionSchema])
def list_permissions(db: Session = Depends(get_db)):
    """List all global permissions."""
    return db.query(GlobalActionPermission).all()


@router.get("/global-permissions/{perm_id}", response_model=GlobalActionPermissionSchema)
def get_permission(perm_id: int, db: Session = Depends(get_db)):
    """Get a single global permission by ID."""
    perm = db.get(GlobalActionPermission, perm_id)
    if not perm:
        raise HTTPException(status_code=404, detail="permission_not_found")
    return perm


@router.post("/global-permissions", response_model=GlobalActionPermissionSchema)
def create_permission(
    payload: GlobalActionPermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new global permission."""
    _require_admin(current_user)
    if not payload.key or not payload.key.strip():
        raise HTTPException(status_code=400, detail="key_required")
    if not payload.module or not payload.module.strip():
        raise HTTPException(status_code=400, detail="module_required")
    key = payload.key.strip()
    module = payload.module.strip()
    if not key.startswith(f"{module}."):
        raise HTTPException(status_code=400, detail="key_module_mismatch")
    perm = GlobalActionPermission(
        key=key,
        module=module,
        description=payload.description,
    )
    db.add(perm)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.exception("Error creating global permission")
        raise HTTPException(status_code=400, detail=f"permission_exists: {e.orig}")
    db.refresh(perm)
    return perm


@router.put("/global-permissions/{perm_id}", response_model=GlobalActionPermissionSchema)
def update_permission(
    perm_id: int,
    payload: GlobalActionPermissionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an existing global permission."""
    _require_admin(current_user)
    perm = db.get(GlobalActionPermission, perm_id)
    if not perm:
        raise HTTPException(status_code=404, detail="permission_not_found")

    data = payload.model_dump(exclude_unset=True)
    if "key" in data:
        key = (data.get("key") or "").strip()
        if not key:
            raise HTTPException(status_code=400, detail="key_required")
        data["key"] = key
    if "module" in data:
        module = (data.get("module") or "").strip()
        if not module:
            raise HTTPException(status_code=400, detail="module_required")
        data["module"] = module
    key_to_check = data.get("key", perm.key)
    module_to_check = data.get("module", perm.module)
    if module_to_check and key_to_check and not key_to_check.startswith(f"{module_to_check}."):
        raise HTTPException(status_code=400, detail="key_module_mismatch")

    for k, v in data.items():
        setattr(perm, k, v)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.exception("Error updating global permission")
        raise HTTPException(status_code=400, detail=f"permission_exists: {e.orig}")
    db.refresh(perm)
    return perm


@router.delete("/global-permissions/{perm_id}", response_model=dict)
def delete_permission(
    perm_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a global permission by ID."""
    _require_admin(current_user)
    perm = db.get(GlobalActionPermission, perm_id)
    if not perm:
        raise HTTPException(status_code=404, detail="permission_not_found")
    db.delete(perm)
    db.commit()
    return {"detail": "Deleted"}
