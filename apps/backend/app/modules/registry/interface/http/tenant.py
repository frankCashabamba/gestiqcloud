from __future__ import annotations

from fastapi import APIRouter

from ...service import discover_manifests
from ...models import ModuleSummary


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleSummary])
def list_enabled_modules_for_tenant():
    # In a future iteration, filter by tenant's plan/flags/permissions.
    items = [m for m in discover_manifests() if "tenant" in m.scopes]
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
