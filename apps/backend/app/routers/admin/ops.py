from __future__ import annotations

import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from app.core.authz import require_scope

router = APIRouter(dependencies=[Depends(require_scope("admin"))])


@router.post("/ops/migrate")
def trigger_migrations():
    """Trigger the Render migrate job if configured.

    Requires env vars:
      - RENDER_API_KEY
      - RENDER_MIGRATE_JOB_ID
    """
    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    if not job_id or not api_key:
        raise HTTPException(status_code=501, detail="render_job_not_configured")

    try:
        resp = requests.post(
            f"https://api.render.com/v1/jobs/{job_id}/runs",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"render_api_unreachable: {e}") from e

    if 200 <= resp.status_code < 300:
        return {"ok": True, "job_id": job_id}
    raise HTTPException(status_code=502, detail=f"render_api_error:{resp.status_code}")

