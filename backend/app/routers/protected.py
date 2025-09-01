"""Module: protected.py

Auto-generated module docstring."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.schemas.configuracion import AuthenticatedUser

router = APIRouter(prefix="/protected", tags=["protected"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def decode_token(token: str) -> AuthenticatedUser:
    """Decode and validate access token using centralized PyJWT service."""
    try:
        payload = PyJWTTokenService().decode_and_validate(token, expected_type="access")
        return AuthenticatedUser(**payload)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    """ Function get_current_user - auto-generated docstring. """
    return decode_token(token)

@router.get("/me", response_model=AuthenticatedUser)
def get_current_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """ Function get_current_user_info - auto-generated docstring. """
    return current_user
