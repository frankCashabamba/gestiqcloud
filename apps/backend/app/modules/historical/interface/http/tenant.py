"""HISTORICAL Module: Tenant HTTP endpoints."""

from __future__ import annotations

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
    from app.modules.historical.application.use_cases import UploadHistoricalFileUseCase

    tid = _require_tenant_id(request)
    uid = _user_id(request)

    if import_type not in ("sales", "purchases", "stock", "daily_sales"):
        raise HTTPException(status_code=400, detail="invalid_import_type")

    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file_too_large")
    filename = file.filename or "unknown"

    return UploadHistoricalFileUseCase(db).execute(
        tenant_id=UUID(tid),
        file_bytes=file_bytes,
        filename=filename,
        import_type=import_type,
        user_id=UUID(uid) if uid else None,
    )


# ── Sales ────────────────────────────────────────────────────────────────────


@router.get("/sales")
def list_sales(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistSalesUseCase

    tid = _require_tenant_id(request)
    return ListHistSalesUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Purchases ────────────────────────────────────────────────────────────────


@router.get("/purchases")
def list_purchases(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistPurchasesUseCase

    tid = _require_tenant_id(request)
    return ListHistPurchasesUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Stock ────────────────────────────────────────────────────────────────────


@router.get("/stock")
def list_stock(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fecha: date | None = Query(None),
    import_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistStockUseCase

    tid = _require_tenant_id(request)
    return ListHistStockUseCase(db).execute(
        tenant_id=UUID(tid),
        page=page,
        page_size=page_size,
        fecha=fecha,
        import_id=UUID(import_id) if import_id else None,
    )


# ── Daily Sales ──────────────────────────────────────────────────────────────


@router.get("/daily-sales")
def list_daily_sales(
    request: Request,
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.modules.historical.application.use_cases import ListHistDailySalesUseCase

    tid = _require_tenant_id(request)
    return ListHistDailySalesUseCase(db).execute(
        tenant_id=UUID(tid),
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    from app.modules.historical.application.use_cases import GetHistDashboardUseCase

    tid = _require_tenant_id(request)
    return GetHistDashboardUseCase(db).execute(UUID(tid))
