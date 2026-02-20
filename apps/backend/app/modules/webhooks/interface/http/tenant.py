"""FastAPI endpoints for webhooks module - Tenant endpoints."""

from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.modules.webhooks.application.schemas import (
    CreateWebhookRequest,
    DeliveryListResponse,
    DeliveryResponse,
    UpdateWebhookRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.modules.webhooks.application.use_cases import (
    CreateWebhookSubscriptionUseCase,
    DeleteWebhookSubscriptionUseCase,
    GetWebhookDeliveryHistoryUseCase,
    ListWebhooksUseCase,
    RetryFailedDeliveryUseCase,
    TestWebhookSubscriptionUseCase,
    UpdateWebhookSubscriptionUseCase,
)
from app.modules.webhooks.domain.exceptions import InvalidWebhookURL, WebhookNotFound

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookSubscriptionCreate(BaseModel):
    """Backwards-compatible request schema used by legacy tests."""

    event: str
    url: str
    secret: str | None = None

    @field_validator("event")
    @classmethod
    def _normalize_event(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if not normalized:
            raise ValueError("event_required")
        return normalized

    @field_validator("url")
    @classmethod
    def _enforce_https(cls, value: str) -> str:
        parsed = urlparse(str(value or ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("webhook_url_must_use_https")
        return value

    @field_validator("secret")
    @classmethod
    def _validate_secret(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 8:
            raise ValueError("secret_too_short")
        return value


class WebhookDeliveryEnqueue(BaseModel):
    """Backwards-compatible enqueue schema used by legacy tests."""

    event: str
    payload: dict


def _is_missing_webhooks_tables(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "webhook_subscriptions" in msg
        or "webhook_deliveries" in msg
        or "undefinedtable" in msg
        or "no existe la relación" in msg
    )


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a webhook subscription."""
    try:
        use_case = CreateWebhookSubscriptionUseCase()
        subscription = use_case.execute(
            tenant_id=current_user["tenant_id"],
            event_type=request.event_type,
            target_url=str(request.target_url),
            secret=request.secret,
            db_session=db,
        )
        return WebhookResponse.from_orm(subscription)
    except InvalidWebhookURL as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhook subscriptions for current tenant."""
    try:
        use_case = ListWebhooksUseCase()
        webhooks, total = use_case.execute(
            tenant_id=current_user["tenant_id"],
            skip=skip,
            limit=limit,
            db_session=db,
        )
        items = [WebhookResponse.from_orm(w) for w in webhooks]
        return WebhookListResponse(items=items, total=total, skip=skip, limit=limit)
    except ProgrammingError as e:
        if _is_missing_webhooks_tables(e):
            # Graceful fallback while tenant DB is pending migrations.
            return WebhookListResponse(items=[], total=0, skip=skip, limit=limit)
        raise


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    request: UpdateWebhookRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update webhook subscription."""
    try:
        use_case = UpdateWebhookSubscriptionUseCase()
        subscription = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user["tenant_id"],
            target_url=str(request.target_url) if request.target_url else None,
            secret=request.secret,
            is_active=request.is_active,
            retry_count=request.retry_count,
            timeout_seconds=request.timeout_seconds,
            db_session=db,
        )
        return WebhookResponse.from_orm(subscription)
    except WebhookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidWebhookURL as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete webhook subscription."""
    try:
        use_case = DeleteWebhookSubscriptionUseCase()
        use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user["tenant_id"],
            db_session=db,
        )
        return None
    except WebhookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{webhook_id}/history", response_model=DeliveryListResponse)
async def get_webhook_history(
    webhook_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get delivery history for a webhook."""
    try:
        use_case = GetWebhookDeliveryHistoryUseCase()
        deliveries, total = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user["tenant_id"],
            limit=limit,
            skip=skip,
            db_session=db,
        )
        items = [DeliveryResponse.from_orm(d) for d in deliveries]
        return DeliveryListResponse(items=items, total=total, webhook_id=webhook_id)
    except WebhookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{webhook_id}/retry", response_model=DeliveryResponse)
async def retry_delivery(
    webhook_id: UUID,
    delivery_id: UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually retry a failed delivery."""
    try:
        use_case = RetryFailedDeliveryUseCase()
        delivery = use_case.execute(
            delivery_id=delivery_id,
            tenant_id=current_user["tenant_id"],
            db_session=db,
        )
        return DeliveryResponse.from_orm(delivery)
    except WebhookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: UUID,
    request: WebhookTestRequest | None = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test webhook by sending sample event."""
    try:
        use_case = TestWebhookSubscriptionUseCase()
        delivery = use_case.execute(
            webhook_id=webhook_id,
            tenant_id=current_user["tenant_id"],
            event_type=request.event_type if request else None,
            db_session=db,
        )

        return WebhookTestResponse(
            delivery_id=delivery.id,
            status_code=delivery.status_code,
            response_body=delivery.response_body,
            success=delivery.is_successful,
            message=(
                "Test webhook queued for delivery" if delivery.id else "Failed to queue delivery"
            ),
        )
    except WebhookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
