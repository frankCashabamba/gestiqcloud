"""FastAPI endpoints for notifications module - Tenant endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.modules.notifications.application.schemas import (
    CreateTemplateRequest,
    MarkReadRequest,
    NotificationListResponse,
    NotificationResponse,
    SendNotificationRequest,
    SendTemplateNotificationRequest,
    TemplateListResponse,
    TemplateResponse,
    UnreadCountResponse,
)
from app.modules.notifications.application.use_cases import (
    ArchiveNotificationUseCase,
    GetUnreadCountUseCase,
    ListNotificationsUseCase,
    MarkAsReadUseCase,
    SendNotificationUseCase,
    SendTemplateNotificationUseCase,
)
from app.modules.notifications.domain.exceptions import (
    DeliveryFailed,
    NotificationNotFound,
    TemplateNotFound,
)
from app.modules.notifications.domain.models import NotificationTemplate

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send", response_model=NotificationResponse, status_code=201)
async def send_notification(
    request: SendNotificationRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Send a notification."""
    try:
        use_case = SendNotificationUseCase()
        notification = await use_case.execute(
            tenant_id=UUID(tenant_id),
            user_id=UUID(current_user["id"]),
            channel=request.channel.value,
            recipient=request.recipient,
            subject=request.subject,
            body=request.body,
            priority=request.priority.value,
            metadata=request.metadata,
            db_session=db,
        )
        return NotificationResponse.model_validate(notification)
    except DeliveryFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send-template", response_model=NotificationResponse, status_code=201)
async def send_template_notification(
    request: SendTemplateNotificationRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Send a notification using a template."""
    try:
        use_case = SendTemplateNotificationUseCase()
        notification = await use_case.execute(
            tenant_id=UUID(tenant_id),
            user_id=UUID(current_user["id"]),
            template_name=request.template_name,
            channel=request.channel.value,
            recipient=request.recipient,
            context=request.context,
            priority=request.priority.value,
            db_session=db,
        )
        return NotificationResponse.model_validate(notification)
    except TemplateNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DeliveryFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """List notifications for current user."""
    use_case = ListNotificationsUseCase()
    notifications, total = use_case.execute(
        tenant_id=UUID(tenant_id),
        user_id=UUID(current_user["id"]),
        skip=skip,
        limit=limit,
        db_session=db,
    )
    items = [NotificationResponse.model_validate(n) for n in notifications]
    return NotificationListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Get unread notification count for current user."""
    use_case = GetUnreadCountUseCase()
    count = use_case.execute(
        tenant_id=UUID(tenant_id),
        user_id=UUID(current_user["id"]),
        db_session=db,
    )
    return UnreadCountResponse(count=count)


@router.post("/mark-read")
def mark_as_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Mark notifications as read."""
    use_case = MarkAsReadUseCase()
    count = use_case.execute(
        tenant_id=UUID(tenant_id),
        user_id=UUID(current_user["id"]),
        notification_ids=request.notification_ids,
        db_session=db,
    )
    return {"updated": count}


@router.post("/{notification_id}/archive", response_model=NotificationResponse)
def archive_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Archive a notification."""
    try:
        use_case = ArchiveNotificationUseCase()
        notification = use_case.execute(
            notification_id=notification_id,
            tenant_id=UUID(tenant_id),
            user_id=UUID(current_user["id"]),
            db_session=db,
        )
        return NotificationResponse.model_validate(notification)
    except NotificationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Create a notification template."""
    template = NotificationTemplate(
        tenant_id=UUID(tenant_id),
        name=request.name,
        channel=request.channel.value,
        subject_template=request.subject_template,
        body_template=request.body_template,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.get("/templates", response_model=TemplateListResponse)
def list_templates(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """List notification templates for current tenant."""
    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.tenant_id == UUID(tenant_id),
    )
    total = query.count()
    templates = query.all()
    items = [TemplateResponse.model_validate(t) for t in templates]
    return TemplateListResponse(items=items, total=total)
