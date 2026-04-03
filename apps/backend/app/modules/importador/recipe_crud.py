"""CRUD for icu_recipe, icu_recipe_draft, icu_recipe_snapshot."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.importador import IcuRecipe, IcuRecipeDraft, IcuRecipeSnapshot


# --- Recipes ---
def create_recipe(db: Session, data: dict) -> IcuRecipe:
    obj = IcuRecipe(**data)
    db.add(obj)
    db.flush()
    return obj


def get_recipe(db: Session, recipe_id: UUID, tenant_id: UUID | None = None) -> IcuRecipe | None:
    q = select(IcuRecipe).where(IcuRecipe.id == recipe_id)
    if tenant_id is not None:
        q = q.where(IcuRecipe.tenant_id == tenant_id)
    return db.scalars(q).first()


def list_recipes(db: Session, tenant_id: UUID, *, include_archived: bool = False):
    q = select(IcuRecipe).where(IcuRecipe.tenant_id == tenant_id)
    if not include_archived:
        q = q.where(IcuRecipe.archived == False)  # noqa: E712
    q = q.order_by(IcuRecipe.updated_at.desc())
    return db.scalars(q).all()


def update_recipe(db: Session, recipe: IcuRecipe, data: dict) -> IcuRecipe:
    for k, v in data.items():
        if v is not None:
            setattr(recipe, k, v)
    db.flush()
    return recipe


# --- Drafts ---
def create_draft(db: Session, data: dict) -> IcuRecipeDraft:
    obj = IcuRecipeDraft(**data)
    db.add(obj)
    db.flush()
    return obj


def get_draft(
    db: Session,
    draft_id: UUID,
    tenant_id: UUID | None = None,
) -> IcuRecipeDraft | None:
    q = select(IcuRecipeDraft).where(IcuRecipeDraft.id == draft_id)
    if tenant_id is not None:
        q = q.where(IcuRecipeDraft.tenant_id == tenant_id)
    return db.scalars(q).first()


def list_drafts(db: Session, recipe_id: UUID, tenant_id: UUID | None = None):
    q = (
        select(IcuRecipeDraft)
        .where(IcuRecipeDraft.recipe_id == recipe_id)
        .order_by(IcuRecipeDraft.updated_at.desc())
    )
    if tenant_id is not None:
        q = q.where(IcuRecipeDraft.tenant_id == tenant_id)
    return db.scalars(q).all()


def update_draft(db: Session, draft: IcuRecipeDraft, data: dict) -> IcuRecipeDraft:
    for k, v in data.items():
        if v is not None:
            setattr(draft, k, v)
    db.flush()
    return draft


# --- Snapshots ---
def create_snapshot(db: Session, data: dict) -> IcuRecipeSnapshot:
    obj = IcuRecipeSnapshot(**data)
    db.add(obj)
    db.flush()
    return obj


def get_snapshot(
    db: Session,
    snapshot_id: UUID,
    tenant_id: UUID | None = None,
) -> IcuRecipeSnapshot | None:
    q = select(IcuRecipeSnapshot).where(IcuRecipeSnapshot.id == snapshot_id)
    if tenant_id is not None:
        q = q.where(IcuRecipeSnapshot.tenant_id == tenant_id)
    return db.scalars(q).first()


def list_snapshots(db: Session, recipe_id: UUID, tenant_id: UUID | None = None):
    q = (
        select(IcuRecipeSnapshot)
        .where(IcuRecipeSnapshot.recipe_id == recipe_id)
        .order_by(IcuRecipeSnapshot.created_at.desc())
    )
    if tenant_id is not None:
        q = q.where(IcuRecipeSnapshot.tenant_id == tenant_id)
    return db.scalars(q).all()


def get_latest_snapshot(
    db: Session,
    recipe_id: UUID,
    tenant_id: UUID | None = None,
) -> IcuRecipeSnapshot | None:
    """Get the most recent snapshot for a recipe."""
    q = (
        select(IcuRecipeSnapshot)
        .where(IcuRecipeSnapshot.recipe_id == recipe_id)
        .order_by(IcuRecipeSnapshot.created_at.desc())
        .limit(1)
    )
    if tenant_id is not None:
        q = q.where(IcuRecipeSnapshot.tenant_id == tenant_id)
    return db.scalars(q).first()
