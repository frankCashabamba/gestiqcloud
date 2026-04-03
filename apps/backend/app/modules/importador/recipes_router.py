"""Recipes API for Importador.

Separa la gestion de recetas/snapshots del flujo de importacion de documentos.
La unica entrada de importacion soportada queda en /importador/run-async.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from . import recipe_crud
from .schemas import (
    DraftCreate,
    DraftOut,
    DraftUpdate,
    RecipeCreate,
    RecipeOut,
    RecipeUpdate,
    SnapshotOut,
)

router = APIRouter(prefix="/importador", tags=["Importador Recipes"])
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


def _tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", None) or {}
    tid = claims.get("tenant_id") or getattr(request.state, "tenant_id", None)
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id no disponible")
    return UUID(str(tid)) if not isinstance(tid, UUID) else tid


def _user_id(request: Request) -> str:
    claims = getattr(request.state, "access_claims", None) or {}
    return str(claims.get("user_id", "unknown"))



@router.post("/recipes", response_model=RecipeOut, dependencies=protected)
def create_recipe(body: RecipeCreate, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.create_recipe(
        db,
        {
            "tenant_id": _tenant_id(request),
            "name": body.name,
            "description": body.description,
            "is_public": body.is_public,
            "created_by": _user_id(request),
        },
    )
    db.commit()
    return recipe


@router.get("/recipes", response_model=list[RecipeOut], dependencies=protected)
def list_recipes(
    request: Request,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return recipe_crud.list_recipes(db, _tenant_id(request), include_archived=include_archived)


@router.get("/recipes/{recipe_id}", response_model=RecipeOut, dependencies=protected)
def get_recipe(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    recipe = recipe_crud.get_recipe(db, recipe_id, tenant_id=_tenant_id(request))
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    return recipe


@router.patch("/recipes/{recipe_id}", response_model=RecipeOut, dependencies=protected)
def update_recipe(
    recipe_id: UUID, body: RecipeUpdate, request: Request, db: Session = Depends(get_db)
):
    recipe = recipe_crud.get_recipe(db, recipe_id, tenant_id=_tenant_id(request))
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    recipe_crud.update_recipe(db, recipe, body.model_dump(exclude_unset=True))
    db.commit()
    return recipe


@router.post("/recipes/{recipe_id}/drafts", response_model=DraftOut, dependencies=protected)
def create_draft(
    recipe_id: UUID, body: DraftCreate, request: Request, db: Session = Depends(get_db)
):
    recipe = recipe_crud.get_recipe(db, recipe_id, tenant_id=_tenant_id(request))
    if not recipe:
        raise HTTPException(404, "Receta no encontrada")
    draft = recipe_crud.create_draft(
        db,
        {
            "tenant_id": _tenant_id(request),
            "recipe_id": recipe_id,
            "prompt_system": body.prompt_system,
            "prompt_user": body.prompt_user,
            "model_config": body.ai_model_config,
            "updated_by": _user_id(request),
        },
    )
    db.commit()
    return draft


@router.get("/recipes/{recipe_id}/drafts", response_model=list[DraftOut], dependencies=protected)
def list_drafts(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    return recipe_crud.list_drafts(db, recipe_id, tenant_id=_tenant_id(request))


@router.get("/drafts/{draft_id}", response_model=DraftOut, dependencies=protected)
def get_draft(draft_id: UUID, request: Request, db: Session = Depends(get_db)):
    draft = recipe_crud.get_draft(db, draft_id, tenant_id=_tenant_id(request))
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    return draft


@router.patch("/drafts/{draft_id}", response_model=DraftOut, dependencies=protected)
def update_draft(
    draft_id: UUID, body: DraftUpdate, request: Request, db: Session = Depends(get_db)
):
    draft = recipe_crud.get_draft(db, draft_id, tenant_id=_tenant_id(request))
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    data = {}
    if body.prompt_system is not None:
        data["prompt_system"] = body.prompt_system
    if body.prompt_user is not None:
        data["prompt_user"] = body.prompt_user
    if body.ai_model_config is not None:
        data["model_config"] = body.ai_model_config
    data["updated_by"] = _user_id(request)
    recipe_crud.update_draft(db, draft, data)
    db.commit()
    return draft


@router.post("/drafts/{draft_id}/snapshot", response_model=SnapshotOut, dependencies=protected)
def create_snapshot(
    draft_id: UUID,
    request: Request,
    version_tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    draft = recipe_crud.get_draft(db, draft_id, tenant_id=_tenant_id(request))
    if not draft:
        raise HTTPException(404, "Borrador no encontrado")
    content = {
        "prompt_system": draft.prompt_system,
        "prompt_user": draft.prompt_user,
        "model_config": draft.model_config,
    }
    prev = recipe_crud.get_latest_snapshot(db, draft.recipe_id, tenant_id=_tenant_id(request))
    if prev and prev.content_json:
        if prev.content_json.get("fingerprint_hash"):
            content["fingerprint_hash"] = prev.content_json["fingerprint_hash"]
        if prev.content_json.get("fingerprint"):
            content["fingerprint"] = prev.content_json["fingerprint"]
    snap = recipe_crud.create_snapshot(
        db,
        {
            "tenant_id": _tenant_id(request),
            "recipe_id": draft.recipe_id,
            "draft_id": draft_id,
            "version_tag": version_tag,
            "content_json": content,
            "created_by": _user_id(request),
        },
    )
    db.commit()
    return snap


@router.get(
    "/recipes/{recipe_id}/snapshots", response_model=list[SnapshotOut], dependencies=protected
)
def list_snapshots(recipe_id: UUID, request: Request, db: Session = Depends(get_db)):
    return recipe_crud.list_snapshots(db, recipe_id, tenant_id=_tenant_id(request))


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut, dependencies=protected)
def get_snapshot(snapshot_id: UUID, request: Request, db: Session = Depends(get_db)):
    snap = recipe_crud.get_snapshot(db, snapshot_id, tenant_id=_tenant_id(request))
    if not snap:
        raise HTTPException(404, "Snapshot no encontrado")
    return snap


@router.get("/save-capabilities", dependencies=protected)
def get_save_capabilities(request: Request, db: Session = Depends(get_db)):
    """Return active tenant modules for save button visibility."""
    from app.models.core.module import CompanyModule, Module

    tenant_id = _tenant_id(request)
    relevant = {"purchases", "expenses", "inventory", "invoicing", "accounting", "suppliers"}
    es_to_en: dict[str, list[str]] = {
        "compras": ["purchases"],
        "gastos": ["expenses"],
        "inventario": ["inventory"],
        "facturación": ["invoicing"],
        "facturacion": ["invoicing"],
        "contabilidad": ["accounting"],
        "proveedores": ["suppliers"],
    }
    rows = (
        db.query(Module.name)
        .join(CompanyModule, CompanyModule.module_id == Module.id)
        .filter(CompanyModule.tenant_id == tenant_id, CompanyModule.active.is_(True))
        .all()
    )
    active_names = {name.lower().strip() for (name,) in rows}
    resolved: set[str] = set()
    for name in active_names:
        resolved.add(name)
        if name in es_to_en:
            resolved.update(es_to_en[name])
    return {mod: mod in resolved or any(mod in n for n in resolved) for mod in relevant}
    from app.models.core.module import CompanyModule, Module

    tenant_id = _tenant_id(request)
    relevant = {"purchases", "expenses", "inventory", "invoicing", "accounting", "suppliers"}
    es_to_en: dict[str, list[str]] = {
        "compras": ["purchases"],
        "gastos": ["expenses"],
        "inventario": ["inventory"],
        "facturación": ["invoicing"],
        "facturacion": ["invoicing"],
        "contabilidad": ["accounting"],
        "proveedores": ["suppliers"],
    }
    rows = (
        db.query(Module.name)
        .join(CompanyModule, CompanyModule.module_id == Module.id)
        .filter(CompanyModule.tenant_id == tenant_id, CompanyModule.active.is_(True))
        .all()
    )
    active_names = {name.lower().strip() for (name,) in rows}
    resolved: set[str] = set()
    for name in active_names:
        resolved.add(name)
        if name in es_to_en:
            resolved.update(es_to_en[name])
    return {mod: mod in resolved or any(mod in n for n in resolved) for mod in relevant}
