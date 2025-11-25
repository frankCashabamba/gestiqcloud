"""Module: roles.py

Auto-generated module docstring."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import GlobalActionPermission
from app.models import RolBase as RolModel
from app.schemas.configuracion import (
    GlobalActionPermissionSchema,
    RolBase,
    RolBaseCreate,
    RolBaseUpdate,
)

from .protected import get_current_user

router = APIRouter(
    prefix="/roles-base",
    tags=["roles"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[RolBase])
def list_roles(db: Session = Depends(get_db)):
    """Function list_roles - auto-generated docstring."""
    return db.query(RolModel).all()


@router.post("/", response_model=RolBase)
def create_role(data: RolBaseCreate, db: Session = Depends(get_db)):
    """Function create_role - auto-generated docstring."""
    # Simple validation for permissions
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
    """Function update_role - auto-generated docstring."""
    role = db.get(RolModel, id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Allow partial updates: only sent fields
    updates = data.model_dump(exclude_unset=True)

    # Validate permissions if they come in the payload
    if "permissions" in updates:
        permissions = updates["permissions"] or []
        if not all(isinstance(p, str) for p in permissions):
            raise HTTPException(status_code=400, detail="All permissions must be strings")

    # Check for duplicate name only if name was sent and changed
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
    """Function delete_role - auto-generated docstring."""
    role = db.get(RolModel, id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"detail": "Deleted"}


@router.get("/global-permissions", response_model=list[GlobalActionPermissionSchema])
def list_permissions(db: Session = Depends(get_db)):
    """Function list_permissions - auto-generated docstring."""
    return db.query(GlobalActionPermission).all()
