from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.importador import (
    IcuRecipe,
    IcuRecipeDraft,
    IcuRecipeSnapshot,
    ImpDocumento,
    ImpStagingLine,
)
from app.models.tenant import Tenant
from app.modules.importador.recipes_router import create_draft as create_recipe_draft
from app.modules.importador.recipes_router import create_snapshot as create_recipe_snapshot
from app.modules.importador.recipes_router import get_draft as get_recipe_draft
from app.modules.importador.recipes_router import get_recipe as get_import_recipe
from app.modules.importador.recipes_router import get_snapshot as get_recipe_snapshot
from app.modules.importador.recipes_router import list_drafts as list_recipe_drafts
from app.modules.importador.recipes_router import list_snapshots as list_recipe_snapshots
from app.modules.importador.router import bulk_patch_staging_lines, patch_staging_line
from app.modules.importador.schemas import BulkStagingPatch, DraftCreate, StagingLinePatch


def _fake_request(tenant_id, user_id: str, *, admin: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={
                "tenant_id": str(tenant_id),
                "user_id": user_id,
                "is_company_admin": admin,
            },
        )
    )


def _create_tenant(db: Session, name: str) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    db.add(
        Tenant(
            id=tenant_id,
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{tenant_id.hex[:8]}",
            base_currency="USD",
        )
    )
    db.commit()
    return tenant_id


def test_recipes_router_scopes_recipe_resources_by_tenant(db: Session, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    tenant_b = _create_tenant(db, "Other Tenant")

    recipe = IcuRecipe(
        tenant_id=tenant_a,
        name="Receta A",
        description="tenant-a recipe",
        created_by="owner-a",
    )
    db.add(recipe)
    db.flush()

    draft = IcuRecipeDraft(
        tenant_id=tenant_a,
        recipe_id=recipe.id,
        prompt_system="system",
        prompt_user="user",
        updated_by="owner-a",
    )
    db.add(draft)
    db.flush()

    snapshot = IcuRecipeSnapshot(
        tenant_id=tenant_a,
        recipe_id=recipe.id,
        draft_id=draft.id,
        version_tag="v1",
        content_json={"prompt_system": "system"},
        created_by="owner-a",
    )
    db.add(snapshot)
    db.commit()

    foreign_request = _fake_request(tenant_b, "owner-b")

    with pytest.raises(HTTPException) as recipe_exc:
        get_import_recipe(recipe.id, foreign_request, db)
    assert recipe_exc.value.status_code == 404

    assert list_recipe_drafts(recipe.id, foreign_request, db) == []
    assert list_recipe_snapshots(recipe.id, foreign_request, db) == []

    with pytest.raises(HTTPException) as draft_exc:
        get_recipe_draft(draft.id, foreign_request, db)
    assert draft_exc.value.status_code == 404

    with pytest.raises(HTTPException) as snapshot_exc:
        get_recipe_snapshot(snapshot.id, foreign_request, db)
    assert snapshot_exc.value.status_code == 404

    with pytest.raises(HTTPException) as create_draft_exc:
        create_recipe_draft(
            recipe.id,
            DraftCreate(prompt_system="x", prompt_user="y", ai_model_config=None),
            foreign_request,
            db,
        )
    assert create_draft_exc.value.status_code == 404

    with pytest.raises(HTTPException) as create_snapshot_exc:
        create_recipe_snapshot(draft.id, foreign_request, "v2", db)
    assert create_snapshot_exc.value.status_code == 404


def test_staging_patch_routes_require_document_access(db: Session, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]

    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="doc.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        usuario_id="owner-a",
    )
    db.add(document)
    db.flush()

    line = ImpStagingLine(
        tenant_id=tenant_id,
        documento_id=document.id,
        line_number=1,
        raw_data={"vendor": "A"},
        estado="PENDING",
    )
    db.add(line)
    db.flush()
    document_id = document.id
    line_id = line.id
    db.commit()

    other_user_request = _fake_request(tenant_id, "owner-b")

    with pytest.raises(HTTPException) as patch_exc:
        patch_staging_line(
            document_id,
            line_id,
            StagingLinePatch(estado="REPROCESS", normalized_data={"vendor": "B"}),
            other_user_request,
            db,
        )
    assert patch_exc.value.status_code == 404

    with pytest.raises(HTTPException) as bulk_exc:
        bulk_patch_staging_lines(
            document_id,
            BulkStagingPatch(line_ids=[line_id], estado="REPROCESS"),
            other_user_request,
            db,
        )
    assert bulk_exc.value.status_code == 404
