# app/core/access_guard.py
from fastapi import HTTPException, Request
from typing import Any, Dict
from jwt import ExpiredSignatureError, InvalidTokenError

from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService


token_service = PyJWTTokenService()

def with_access_claims(request: Request) -> Dict[str, Any]:
    # 1) extrae Authorization
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = token_service.decode_and_validate(token, expected_type="access")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    request.state.access_claims = claims
    return claims
