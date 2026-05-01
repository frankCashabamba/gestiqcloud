"""Admin E-Invoicing endpoints.

Endpoints administrativos para configurar SRI (Ecuador) y SII (España)
por tenant: subida de certificado .p12 y gestión de settings.

Mounted under ``/api/v1/admin`` → final paths:
- ``POST /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/certificate``
- ``GET  /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/settings``
- ``PUT  /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/settings``

donde ``type`` ∈ {"sri", "sii"}.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.einvoicing.country_settings import EInvoicingCountrySettings
from app.services.certificate_manager import certificate_manager

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/companies/{tenant_id}/einvoicing",
    tags=["Admin E-Invoicing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# type (path) → ISO country code stored in EInvoicingCountrySettings.country
_TYPE_TO_COUNTRY = {"sri": "EC", "sii": "ES"}


def _validate_tenant_id(tenant_id: str) -> UUID:
    try:
        return UUID(str(tenant_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_tenant_id") from exc


def _resolve_country(type_: str) -> str:
    country = _TYPE_TO_COUNTRY.get(type_.lower())
    if not country:
        raise HTTPException(status_code=400, detail="invalid_einvoicing_type")
    return country


def _run_async(coro):
    """Bridge async helpers a contexto sync de FastAPI."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
    except RuntimeError:
        pass
    return asyncio.run(coro)


def _get_settings(
    db: Session, tenant_id: UUID, country: str
) -> EInvoicingCountrySettings | None:
    return db.execute(
        select(EInvoicingCountrySettings).where(
            EInvoicingCountrySettings.tenant_id == tenant_id,
            EInvoicingCountrySettings.country == country,
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CertificateUploadOut(BaseModel):
    tenant_id: UUID
    type: str
    country: str
    cert_ref: str
    alias: str | None = None
    uploaded_at: datetime


class EInvoicingSettingsOut(BaseModel):
    tenant_id: UUID
    type: str
    country: str
    is_enabled: bool
    environment: str
    api_endpoint: str | None = None
    username: str | None = None
    has_certificate: bool = False
    has_password: bool = False
    max_retries: int = 5
    retry_backoff_seconds: int = 300
    validation_rules: dict[str, Any] | None = None


class EInvoicingSettingsIn(BaseModel):
    is_enabled: bool | None = None
    environment: str | None = None  # "STAGING" | "PRODUCTION"
    api_endpoint: str | None = None
    username: str | None = None
    max_retries: int | None = None
    retry_backoff_seconds: int | None = None
    validation_rules: dict[str, Any] | None = None


def _to_out(
    settings: EInvoicingCountrySettings, tenant_id: UUID, type_: str
) -> EInvoicingSettingsOut:
    return EInvoicingSettingsOut(
        tenant_id=tenant_id,
        type=type_,
        country=settings.country,
        is_enabled=bool(settings.is_enabled),
        environment=settings.environment or "STAGING",
        api_endpoint=settings.api_endpoint,
        username=settings.username,
        has_certificate=settings.certificate_file_id is not None,
        has_password=bool(settings.certificate_password_encrypted)
        or bool(settings.password_encrypted),
        max_retries=settings.max_retries or 5,
        retry_backoff_seconds=settings.retry_backoff_seconds or 300,
        validation_rules=settings.validation_rules,
    )


# ---------------------------------------------------------------------------
# Endpoints — Certificate upload
# ---------------------------------------------------------------------------


@router.post(
    "/{type}/certificate",
    response_model=CertificateUploadOut,
    status_code=201,
)
def upload_einvoicing_certificate(
    request: Request,
    tenant_id: str = Path(..., description="Tenant UUID"),
    type: str = Path(..., pattern="^(sri|sii)$", description="sri | sii"),
    file: UploadFile = File(..., description="Archivo .p12/.pfx"),
    password: str = Form(..., description="Contraseña del certificado"),
    alias: str | None = Form(None, description="Alias opcional"),
):
    tid = _validate_tenant_id(tenant_id)
    country = _resolve_country(type)

    filename = (file.filename or "").lower()
    if filename and not (filename.endswith(".p12") or filename.endswith(".pfx")):
        raise HTTPException(status_code=400, detail="invalid_file_extension")

    cert_data = file.file.read()
    if not cert_data:
        raise HTTPException(status_code=400, detail="empty_certificate_file")

    claims = getattr(request.state, "access_claims", {}) or {}
    logger.info(
        "AUDIT einvoicing.upload_certificate | tenant_id=%s user_id=%s type=%s alias=%s ts=%s",
        tid,
        claims.get("user_id"),
        type,
        alias,
        datetime.now(UTC).isoformat(),
    )

    try:
        cert_ref = _run_async(
            certificate_manager.store_certificate(
                tenant_id=tid,
                country=country,
                cert_data=cert_data,
                password=password,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensa
        logger.exception("upload_certificate_failed")
        raise HTTPException(status_code=500, detail=f"upload_failed: {e}") from e

    return CertificateUploadOut(
        tenant_id=tid,
        type=type,
        country=country,
        cert_ref=cert_ref,
        alias=alias,
        uploaded_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Endpoints — SRI/SII settings
# ---------------------------------------------------------------------------


@router.get("/{type}/settings", response_model=EInvoicingSettingsOut)
def get_einvoicing_settings(
    tenant_id: str = Path(...),
    type: str = Path(..., pattern="^(sri|sii)$"),
    db: Session = Depends(get_db),
):
    tid = _validate_tenant_id(tenant_id)
    country = _resolve_country(type)

    settings = _get_settings(db, tid, country)
    if not settings:
        raise HTTPException(status_code=404, detail="einvoicing_settings_not_found")
    return _to_out(settings, tid, type)


@router.put("/{type}/settings", response_model=EInvoicingSettingsOut)
def update_einvoicing_settings(
    payload: EInvoicingSettingsIn,
    request: Request,
    tenant_id: str = Path(...),
    type: str = Path(..., pattern="^(sri|sii)$"),
    db: Session = Depends(get_db),
):
    tid = _validate_tenant_id(tenant_id)
    country = _resolve_country(type)

    if payload.environment is not None and payload.environment.upper() not in (
        "STAGING",
        "PRODUCTION",
    ):
        raise HTTPException(status_code=400, detail="invalid_environment")

    settings = _get_settings(db, tid, country)
    created = False
    if not settings:
        settings = EInvoicingCountrySettings(
            tenant_id=tid,
            country=country,
            is_enabled=False,
            environment="STAGING",
        )
        db.add(settings)
        created = True

    if payload.is_enabled is not None:
        settings.is_enabled = bool(payload.is_enabled)
    if payload.environment is not None:
        settings.environment = payload.environment.upper()
    if payload.api_endpoint is not None:
        settings.api_endpoint = payload.api_endpoint or None
    if payload.username is not None:
        settings.username = payload.username or None
    if payload.max_retries is not None:
        settings.max_retries = int(payload.max_retries)
    if payload.retry_backoff_seconds is not None:
        settings.retry_backoff_seconds = int(payload.retry_backoff_seconds)
    if payload.validation_rules is not None:
        settings.validation_rules = payload.validation_rules

    claims = getattr(request.state, "access_claims", {}) or {}
    user_id = claims.get("user_id")
    if user_id:
        try:
            settings.configured_by = UUID(str(user_id))
        except Exception:
            pass
    settings.configured_at = datetime.now(UTC)

    db.commit()
    db.refresh(settings)

    logger.info(
        "AUDIT einvoicing.update_settings | tenant_id=%s user_id=%s type=%s created=%s ts=%s",
        tid,
        user_id,
        type,
        created,
        datetime.now(UTC).isoformat(),
    )
    return _to_out(settings, tid, type)

