"""HISTORICAL Module: Tenant HTTP endpoints."""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(
    prefix="/historical",
    tags=["Historical"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _require_tenant_id(request: Request) -> str:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        if tid is not None:
            return str(tid)
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="missing_tenant")


def _user_id(request: Request) -> str | None:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        uid = claims.get("user_id") if isinstance(claims, dict) else None
        return str(uid) if uid is not None else None
    except Exception:
        return None


# ── Imports ──────────────────────────────────────────────────────────────────


@router.get("/imports")
def list_imports(request: Request, db: Session = Depends(get_db)):
    from app.modules.historical.application.use_cases import ListImportsUseCase

    tid = _require_tenant_id(request)
    return ListImportsUseCase(db).execute(UUID(tid))


@router.get("/imports/{import_id}")
def get_import(import_id: str, request: Request, db: Session = Depends(get_db)):
    from app.modules.historical.application.use_cases import GetImportUseCase

    tid = _require_tenant_id(request)
    result = GetImportUseCase(db).execute(UUID(tid), UUID(import_id))
    if not result:
        raise HTTPException(status_code=404, detail="import_not_found")
    return result


@router.delete("/imports/{import_id}")
def delete_import(import_id: str, request: Request, db: Session = Depends(get_db)):
    from app.modules.historical.application.use_cases import DeleteImportUseCase

    tid = _require_tenant_id(request)
    deleted = DeleteImportUseCase(db).execute(UUID(tid), UUID(import_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="import_not_found")
    return {"ok": True}


# ── Upload ───────────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    import_type: str = Form(...),
    db: Session = Depends(get_db),
):
    from app.config.database import SessionLocal
    from app.modules.historical.application.use_cases import UploadHistoricalFileUseCase

    tid = _require_tenant_id(request)
    uid = _user_id(request)

    if import_type not in ("sales", "purchases", "stock", "daily_sales"):
        raise HTTPException(status_code=400, detail="invalid_import_type")

    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file_too_large")
    filename = file.filename or "unknown"

    # Capture the RLS context set on the request-scoped session so we can
    # replicate it in the worker-thread session (SQLAlchemy sessions are not
    # thread-safe; we open a dedicated one inside the thread).
    rls_info = {
        "tenant_id": db.info.get("tenant_id"),
        "user_id": db.info.get("user_id"),
        "bypass_rls": bool(db.info.get("bypass_rls", False)),
    }

    def _run_in_thread() -> dict:
        thread_db = SessionLocal()
        try:
            thread_db.info.update(rls_info)
            result = UploadHistoricalFileUseCase(thread_db).execute(
                tenant_id=UUID(tid),
                file_bytes=file_bytes,
                filename=filename,
                import_type=import_type,
                user_id=UUID(uid) if uid else None,
            )
            return result
        finally:
            thread_db.close()

    try:
        return await asyncio.to_thread(_run_in_thread)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("duplicate_file_hash:"):
            existing_id = msg.split(":", 1)[1]
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_file_hash", "existing_id": existing_id},
            )
        # legacy basic-dedup error
        if msg.startswith("Duplicate historical import:"):
            existing_id = msg.split(":", 1)[1].strip()
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_import", "existing_id": existing_id},
            )
        raise HTTPException(status_code=422, detail=msg)


# ── Sales ────────────────────────────────────────────────────────────────────


@router.get("/sales")
def list_sales(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistSalesUseCase

    tid = _require_tenant_id(request)
    return ListHistSalesUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Purchases ────────────────────────────────────────────────────────────────


@router.get("/purchases")
def list_purchases(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistPurchasesUseCase

    tid = _require_tenant_id(request)
    return ListHistPurchasesUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Stock ────────────────────────────────────────────────────────────────────


@router.get("/stock")
def list_stock(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    date_filter: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistStockUseCase

    tid = _require_tenant_id(request)
    return ListHistStockUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        date_filter=date_filter,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Daily Sales ──────────────────────────────────────────────────────────────


@router.get("/daily-sales")
def list_daily_sales(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistDailySalesUseCase

    tid = _require_tenant_id(request)
    return ListHistDailySalesUseCase(db).execute(
        tenant_id=UUID(tid),
        date_from=date_from,
        date_to=date_to,
    )


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    from app.modules.historical.application.use_cases import GetHistDashboardUseCase

    tid = _require_tenant_id(request)
    return GetHistDashboardUseCase(db).execute(UUID(tid))
