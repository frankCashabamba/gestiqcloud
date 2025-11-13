from __future__ import annotations

from fastapi import APIRouter

from ...service import discover_manifests
from ...models import ModuleSummary


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleSummary])
def list_all_modules():
    items = discover_manifests()
    return [
        ModuleSummary(
            id=m.id,
            name=m.name,
            version=m.version,
            scopes=m.scopes,
            permissions=m.permissions,
            plan_flags=m.plan_flags,
            ui=m.ui,
        )
        for m in items
    ]
