"""Webhook management endpoints for tenants"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, validator
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_from_request

logger = logging.getLogger(__name__)

try:
    from apps.backend.celery_app import celery_app
except Exception:
    celery_app = None


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class WebhookSubscriptionCreate(BaseModel):
    """Create webhook subscription request"""

    event: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=10, max_length=2048)
    secret: Optional[str] = Field(None, max_length=500)

    @validator("event")
    def validate_event(cls, v):
        """Validate event format"""
        if not v or not isinstance(v, str):
            raise ValueError("event must be a non-empty string")
        if " " in v:
            raise ValueError("event cannot contain spaces")
        return v.lower().strip()

    @validator("url")
    def validate_url(cls, v):
        """Validate URL is HTTPS"""
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("URL must use HTTPS protocol")
        if len(v) > 2048:
            raise ValueError("URL is too long")
        return v

    @validator("secret")
    def validate_secret(cls, v):
        """Validate secret format"""
        if v is not None:
            v = v.strip()
            if len(v) < 8:
                raise ValueError("secret must be at least 8 characters")
            if len(v) > 500:
                raise ValueError("secret is too long")
        return v


class WebhookSubscriptionResponse(BaseModel):
    """Webhook subscription response"""

    id: str
    event: str
    url: str
    secret: Optional[str]  # Masked or null
    active: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class WebhookDeliveryEnqueue(BaseModel):
    """Enqueue webhook deliveries request"""

    event: str = Field(..., min_length=1, max_length=100)
    payload: dict = Field(...)

    @validator("event")
    def validate_event(cls, v):
        """Validate event format"""
        if not v or not isinstance(v, str):
            raise ValueError("event must be a non-empty string")
        if " " in v:
            raise ValueError("event cannot contain spaces")
        return v.lower().strip()

    @validator("payload")
    def validate_payload(cls, v):
        """Validate payload is JSON serializable"""
        if not isinstance(v, dict):
            raise ValueError("payload must be a dictionary")
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            raise ValueError("payload must be JSON serializable")
        return v


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery enqueue response"""

    queued: bool
    count: int
    message: Optional[str] = None


class WebhookDeliveryStatusResponse(BaseModel):
    """Webhook delivery status response"""

    id: str
    event: str
    status: str
    attempts: int
    target_url: str
    last_error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================================
# Subscriptions Endpoints
# ============================================================================


@router.post(
    "/subscriptions",
    response_model=WebhookSubscriptionResponse,
    status_code=201,
    summary="Create webhook subscription",
)
def create_subscription(
    payload: WebhookSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a new webhook subscription for a tenant.

    Returns:
        - 201: Subscription created successfully
        - 400: Invalid input (URL not HTTPS, invalid event, secret too short, etc.)
        - 409: Duplicate subscription (same event+url already active)
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    # Check for duplicate subscription
    existing = db.execute(
        text(
            """
            SELECT id FROM webhook_subscriptions
            WHERE tenant_id = :tid AND event = :event AND url = :url AND active = true
            LIMIT 1
            """
        ),
        {"tid": tenant_id, "event": payload.event, "url": payload.url},
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="duplicate_subscription",
        )

    # Create subscription
    try:
        result = db.execute(
            text(
                """
                INSERT INTO webhook_subscriptions(tenant_id, event, url, secret, active)
                VALUES (:tid, :event, :url, :secret, true)
                RETURNING id::text, event, url, secret, active, created_at::text
                """
            ),
            {
                "tid": tenant_id,
                "event": payload.event,
                "url": payload.url,
                "secret": payload.secret,
            },
        ).first()

        db.commit()

        return WebhookSubscriptionResponse(
            id=result[0],
            event=result[1],
            url=result[2],
            secret="***" if result[3] else None,  # Mask secret in response
            active=result[4],
            created_at=result[5],
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="failed_to_create_subscription")


@router.get(
    "/subscriptions",
    response_model=list[WebhookSubscriptionResponse],
    summary="List webhook subscriptions",
)
def list_subscriptions(
    request: Request,
    event: Optional[str] = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    """
    List active webhook subscriptions for a tenant.

    Query Parameters:
        - event: Optional event filter

    Returns:
        - 200: List of subscriptions
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    query = """
        SELECT id::text, event, url, secret, active, created_at::text
        FROM webhook_subscriptions
        WHERE tenant_id = :tid AND active = true
    """
    params = {"tid": tenant_id}

    if event:
        query += " AND event = :event"
        params["event"] = event.lower().strip()

    query += " ORDER BY created_at DESC"

    try:
        rows = db.execute(text(query), params).fetchall()

        return [
            WebhookSubscriptionResponse(
                id=row[0],
                event=row[1],
                url=row[2],
                secret="***" if row[3] else None,  # Mask secret in response
                active=row[4],
                created_at=row[5],
            )
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        raise HTTPException(status_code=500, detail="failed_to_list_subscriptions")


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=204,
    summary="Delete webhook subscription",
)
def delete_subscription(
    subscription_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Soft delete a webhook subscription (set active=false).

    Returns:
        - 204: Subscription deleted successfully
        - 404: Subscription not found
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    try:
        result = db.execute(
            text(
                """
                UPDATE webhook_subscriptions
                SET active = false
                WHERE id = CAST(:sub_id AS uuid) AND tenant_id = :tid
                """
            ),
            {"sub_id": subscription_id, "tid": tenant_id},
        )

        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="subscription_not_found")

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error deleting subscription: {e}")
        raise HTTPException(status_code=500, detail="failed_to_delete_subscription")


# ============================================================================
# Deliveries Endpoints
# ============================================================================


@router.post(
    "/deliveries",
    response_model=WebhookDeliveryResponse,
    status_code=202,
    summary="Enqueue webhook deliveries",
)
def enqueue_delivery(
    payload: WebhookDeliveryEnqueue,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Enqueue webhook deliveries for all active subscriptions matching the event.

    Returns:
        - 202: Deliveries queued successfully
        - 400: Invalid input
        - 404: No active subscriptions for event
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    # Find all active subscriptions for this event
    try:
        subs = db.execute(
            text(
                """
                SELECT id::text, url, secret FROM webhook_subscriptions
                WHERE tenant_id = :tid AND event = :event AND active = true
                """
            ),
            {"tid": tenant_id, "event": payload.event},
        ).fetchall()

        if not subs:
            raise HTTPException(
                status_code=404,
                detail="no_active_subscriptions_for_event",
            )

        count = 0
        payload_json = json.dumps(payload.payload)

        for sub_id, url, secret in subs:
            # Create delivery record
            delivery_result = db.execute(
                text(
                    """
                    INSERT INTO webhook_deliveries(
                        tenant_id, event, payload, target_url, secret, status
                    )
                    VALUES (:tid, :event, :payload::jsonb, :url, :secret, 'PENDING')
                    RETURNING id::text
                    """
                ),
                {
                    "tid": tenant_id,
                    "event": payload.event,
                    "payload": payload_json,
                    "url": url,
                    "secret": secret,
                },
            ).first()

            delivery_id = delivery_result[0]
            count += 1

            # Enqueue Celery task if available
            if celery_app:
                try:
                    celery_app.send_task(
                        "apps.backend.app.modules.webhooks.tasks.deliver",
                        args=[delivery_id],
                    )
                    logger.info(f"Queued delivery task: {delivery_id}")
                except Exception as e:
                    logger.error(f"Failed to queue Celery task: {e}")

        db.commit()

        return WebhookDeliveryResponse(
            queued=True,
            count=count,
            message=f"Enqueued {count} deliveries",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enqueueing deliveries: {e}")
        raise HTTPException(status_code=500, detail="failed_to_enqueue_deliveries")


@router.get(
    "/deliveries",
    response_model=list[WebhookDeliveryStatusResponse],
    summary="List webhook deliveries",
)
def list_deliveries(
    request: Request,
    event: Optional[str] = Query(None, min_length=1, max_length=100),
    status: Optional[str] = Query(None, regex="^(PENDING|SENDING|SENT|DELIVERED|FAILED)$"),
    db: Session = Depends(get_db),
):
    """
    List webhook deliveries for a tenant.

    Query Parameters:
        - event: Optional event filter
        - status: Optional status filter (PENDING, SENDING, SENT, DELIVERED, FAILED)

    Returns:
        - 200: List of deliveries
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    query = """
        SELECT 
            id::text, event, status, attempts, target_url, last_error,
            created_at::text, updated_at::text
        FROM webhook_deliveries
        WHERE tenant_id = :tid
    """
    params = {"tid": tenant_id}

    if event:
        query += " AND event = :event"
        params["event"] = event.lower().strip()

    if status:
        query += " AND status = :status"
        params["status"] = status.upper()

    query += " ORDER BY created_at DESC LIMIT 100"

    try:
        rows = db.execute(text(query), params).fetchall()

        return [
            WebhookDeliveryStatusResponse(
                id=row[0],
                event=row[1],
                status=row[2],
                attempts=row[3],
                target_url=row[4],
                last_error=row[5],
                created_at=row[6],
                updated_at=row[7],
            )
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error listing deliveries: {e}")
        raise HTTPException(status_code=500, detail="failed_to_list_deliveries")


@router.get(
    "/deliveries/{delivery_id}",
    response_model=WebhookDeliveryStatusResponse,
    summary="Get webhook delivery details",
)
def get_delivery(
    delivery_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get details of a specific webhook delivery.

    Returns:
        - 200: Delivery details
        - 404: Delivery not found
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    try:
        row = db.execute(
            text(
                """
                SELECT 
                    id::text, event, status, attempts, target_url, last_error,
                    created_at::text, updated_at::text
                FROM webhook_deliveries
                WHERE id = CAST(:delivery_id AS uuid) AND tenant_id = :tid
                """
            ),
            {"delivery_id": delivery_id, "tid": tenant_id},
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="delivery_not_found")

        return WebhookDeliveryStatusResponse(
            id=row[0],
            event=row[1],
            status=row[2],
            attempts=row[3],
            target_url=row[4],
            last_error=row[5],
            created_at=row[6],
            updated_at=row[7],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving delivery: {e}")
        raise HTTPException(status_code=500, detail="failed_to_retrieve_delivery")


@router.post(
    "/deliveries/{delivery_id}/retry",
    response_model=dict,
    status_code=202,
    summary="Retry failed webhook delivery",
)
def retry_delivery(
    delivery_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Manually retry a failed webhook delivery.

    Returns:
        - 202: Retry queued
        - 404: Delivery not found
        - 400: Delivery not in failed state
        - 403: Missing tenant context
    """
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

    try:
        # Verify delivery exists and is in failed state
        delivery = db.execute(
            text(
                """
                SELECT id::text, status FROM webhook_deliveries
                WHERE id = CAST(:delivery_id AS uuid) AND tenant_id = :tid
                """
            ),
            {"delivery_id": delivery_id, "tid": tenant_id},
        ).first()

        if not delivery:
            raise HTTPException(status_code=404, detail="delivery_not_found")

        if delivery[1] not in ("FAILED", "SENT"):
            raise HTTPException(
                status_code=400,
                detail="delivery_not_in_failed_state",
            )

        # Reset delivery status and attempts
        db.execute(
            text(
                """
                UPDATE webhook_deliveries
                SET status = 'PENDING', attempts = 0, last_error = NULL
                WHERE id = CAST(:delivery_id AS uuid)
                """
            ),
            {"delivery_id": delivery_id},
        )

        db.commit()

        # Re-enqueue task
        if celery_app:
            try:
                celery_app.send_task(
                    "apps.backend.app.modules.webhooks.tasks.deliver",
                    args=[delivery_id],
                )
            except Exception as e:
                logger.error(f"Failed to queue retry task: {e}")

        return {"queued": True, "message": "Retry queued"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error retrying delivery: {e}")
        raise HTTPException(status_code=500, detail="failed_to_retry_delivery")
