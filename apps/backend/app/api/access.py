# app/api/v1/auth/access.py (alias deprecado → delega a /auth/refresh)
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.api.v1.tenant.auth import refresh as tenant_refresh
from app.api.v1.admin.auth import refresh as admin_refresh

router = APIRouter(prefix="/auth", tags=["Auth"])

def _deprecate(resp: Response):
    resp.headers["Deprecation"] = "true"
    resp.headers["Sunset"] = "Wed, 01 Oct 2025 00:00:00 GMT"
    resp.headers["Link"] = "<https://docs.example.com/changelog#renew-deprecated>; rel="deprecation""

@router.post("/access/renew", deprecated=True)
def access_renew(request: Request, response: Response, db: Session = Depends(get_db)):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        payload = PyJWTTokenService().decode_and_validate(rt, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    _deprecate(response)
    kind = str(payload.get("kind") or "tenant")
    if kind == "admin":
        return admin_refresh(request=request, response=response)
    return tenant_refresh(request=request, response=response)
