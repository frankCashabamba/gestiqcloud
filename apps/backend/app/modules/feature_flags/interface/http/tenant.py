"""Feature flags API for tenant frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.feature_flags.dependencies import get_feature_flags
from app.modules.feature_flags.service import ResolvedFlags

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@router.get("")
def list_flags(flags: ResolvedFlags = Depends(get_feature_flags)):
    return {"flags": flags.to_dict()}
