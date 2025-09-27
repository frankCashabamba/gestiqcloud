from __future__ import annotations

from typing import Any, Dict, Literal, Mapping, Optional

from fastapi import Request, Response

from app.config.settings import settings
from app.core.csrf import issue_csrf_token
from app.modules.identity.application.ports import RefreshTokenRepo, TokenService


def ensure_session(request: Request) -> Dict[str, Any]:
    """Ensure request.state.session exists and return it."""
    if not hasattr(request, "state") or not hasattr(request.state, "session") or request.state.session is None:
        request.state.session = {}
    return request.state.session  # type: ignore[return-value]


def set_csrf_cookie(response: Response, token: str, *, path: str = "/") -> None:
    """Set a JS-readable CSRF cookie with sensible defaults."""
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="lax",
        secure=not settings.debug,
        path=path,
    )


def issue_csrf_and_cookie(request: Request, response: Response, *, path: str = "/") -> str:
    """Issue a CSRF token, store it in session and set cookie."""
    ensure_session(request)
    token = issue_csrf_token(request)
    set_csrf_cookie(response, token, path=path)
    return token


def rotate_refresh(
    request: Request,
    response: Response,
    *,
    token_service: TokenService,
    repo: RefreshTokenRepo,
    expected_kind: Literal["admin", "tenant"],
    cookie_path: str,
) -> Dict[str, Any]:
    """Common refresh rotation flow shared by admin and tenant endpoints."""
    token = request.cookies.get("refresh_token")
    if not token:
        from fastapi import HTTPException
        from app.core.i18n import t

        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    try:
        payload: Mapping[str, object] = token_service.decode_and_validate(token, expected_type="refresh")
    except Exception:
        from fastapi import HTTPException
        from app.core.i18n import t

        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    # jti
    jti_obj = payload.get("jti")
    if not isinstance(jti_obj, str) or not jti_obj:
        from fastapi import HTTPException
        from app.core.i18n import t

        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))
    jti: str = jti_obj

    # family_id via DB or payload fallback
    family_from_db: Optional[str] = repo.get_family(jti=jti)
    fam_payload_obj = payload.get("family_id")
    fam_payload: Optional[str] = fam_payload_obj if isinstance(fam_payload_obj, str) else None
    family_id: Optional[str] = family_from_db or fam_payload
    if family_id is None:
        from fastapi import HTTPException
        from app.core.i18n import t

        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    # Fingerprint enforcement optional
    if getattr(settings, "REFRESH_ENFORCE_FINGERPRINT", False):
        from app.core.refresh import token_fingerprint_matches_request

        ua = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else ""
        if not token_fingerprint_matches_request(jti, ua, ip):
            repo.revoke_family(family_id=family_id)
            from fastapi import HTTPException
            from app.core.i18n import t

            raise HTTPException(status_code=401, detail=t(request, "compromised_refresh_token"))

    # Reuse/revoked detection
    if repo.is_reused_or_revoked(jti=jti):
        repo.revoke_family(family_id=family_id)
        from fastapi import HTTPException
        from app.core.i18n import t

        raise HTTPException(status_code=401, detail=t(request, "compromised_refresh_token"))

    # Rotation
    repo.mark_used(jti=jti)
    new_jti = repo.issue_token(
        family_id=family_id,
        prev_jti=jti,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    # Access + refresh
    minimal = {
        "sub": payload.get("sub"),
        "user_id": payload.get("user_id"),
        # Propaga tenant_id si venía en el refresh (para claims completos en access)
        "tenant_id": payload.get("tenant_id"),
    }
    access = token_service.issue_access({**minimal, "kind": expected_kind})
    new_refresh = token_service.issue_refresh(
        {**minimal, "kind": expected_kind, "family_id": family_id},
        jti=new_jti,
        prev_jti=jti,
    )

    from app.core.auth_http import set_refresh_cookie

    set_refresh_cookie(response, new_refresh, path=cookie_path)
    return {"access_token": access, "token_type": "bearer"}
