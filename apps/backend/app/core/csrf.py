import secrets
from fastapi import Request


def issue_csrf_token(request: Request) -> str:
    token = secrets.token_urlsafe(24)
    request.state.session["csrf"] = token
    request.state.session_dirty = True
    return token
