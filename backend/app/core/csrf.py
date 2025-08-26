import secrets
from fastapi import Request, HTTPException

def issue_csrf_token(request: Request) -> str:
    token = secrets.token_urlsafe(24)
    request.state.session["csrf"] = token
    request.state.session_dirty = True
    return token

def verify_csrf(request: Request):
    sent = request.headers.get("X-CSRF-Token")
    expected = request.state.session.get("csrf")
    if not sent or not expected or sent != expected:
        raise HTTPException(status_code=403, detail="CSRF verification failed")
