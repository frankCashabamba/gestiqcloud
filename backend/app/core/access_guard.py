# app/core/access_guard.py
from fastapi import  HTTPException, Request
from app.core.refresh import decode_and_validate  # o tu verificador de access
from typing import Dict

def with_access_claims(request: Request) -> Dict:
    # 1) extrae Authorization
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    # 2) valida/decodifica (expected_type="access" si lo distingues)
    claims = decode_and_validate(token, expected_type="access")
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Invalid token")
    # 3) deja los claims disponibles
    request.state.access_claims = claims
    return claims
