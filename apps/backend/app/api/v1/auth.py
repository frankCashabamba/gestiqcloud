import logging

# Reuse existing concrete login handlers
from app.api.v1.admin.auth import admin_login as _admin_login
from app.api.v1.tenant.auth import tenant_login as _tenant_login
from app.config.database import get_db
from app.config.settings import settings
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("app.api.auth_alias")

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginPayload(BaseModel):
    identificador: str
    password: str


@router.post("/login")
def universal_login(
    data: LoginPayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Compat layer: /api/v1/auth/login
    Tries admin login first; on 401 falls back to tenant login.
    """
    # Try tenant first (most common), then admin
    try:
        return _tenant_login(data=data, request=request, response=response, db=db)
    except HTTPException as e:
        if e.status_code != 401:
            logger.exception("Tenant login HTTPException: %s", getattr(e, "detail", e))
            # In non-production, surface a hint to aid tests
            if settings.ENV != "production":
                hint = f"tenant_login_http:{getattr(e, 'detail', str(e))}"
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail,
                    headers={"X-Debug-Error": hint},
                )
            raise
    except Exception as e:  # unexpected crash in tenant login
        logger.exception("Tenant login crashed")
        if settings.ENV != "production":
            response.headers["X-Debug-Error"] = f"tenant_login_crash:{e}"
        # continue to admin fallback

    # Fallback to admin
    try:
        return _admin_login(data=data, request=request, response=response, db=db)
    except HTTPException as e:
        if e.status_code != 401:
            logger.exception("Admin login HTTPException: %s", getattr(e, "detail", e))
            if settings.ENV != "production":
                hint = f"admin_login_http:{getattr(e, 'detail', str(e))}"
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail,
                    headers={"X-Debug-Error": hint},
                )
            raise
        # Normalize 401
        raise HTTPException(status_code=401, detail="invalid_credentials")
    except Exception as e:
        logger.exception("Admin login crashed")
        if settings.ENV != "production":
            hint = f"admin_login_crash:{e}"
            raise HTTPException(
                status_code=500,
                detail="login_internal_error",
                headers={"X-Debug-Error": hint},
            )
        raise HTTPException(status_code=500, detail="login_internal_error")
