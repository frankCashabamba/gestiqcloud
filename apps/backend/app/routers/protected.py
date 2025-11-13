"""Module: protected.py

Auto-generated module docstring."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from jwt import ExpiredSignatureError, InvalidTokenError
from app.modules.identity.infrastructure.jwt_service import JwtService
from app.schemas.configuracion import AuthenticatedUser

router = APIRouter(prefix="/protected", tags=["protected"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_token(token: str) -> AuthenticatedUser:
    """Decode and validate access token using centralized JwtService and map to AuthenticatedUser."""
    try:
        payload = JwtService().decode(token, expected_kind="access")
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )

    # Derive required fields
    uid = payload.get("user_id")
    if isinstance(uid, str) and uid.isdigit():
        uid = int(uid)
    if not isinstance(uid, (int,)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )

    kind = payload.get("kind") or payload.get("scope") or "tenant"
    user_type = "admin" if kind == "admin" else "tenant"
    is_super = bool(payload.get("is_superadmin") or False)

    return AuthenticatedUser(
        user_id=uid,
        is_superadmin=is_super,
        user_type=user_type,
        tenant_id=payload.get("tenant_id"),
        empresa_slug=payload.get("empresa_slug"),
        plantilla=payload.get("plantilla"),
        es_admin_empresa=payload.get("es_admin_empresa"),
        permisos=payload.get("permisos") or {},
        nombre=payload.get("nombre"),
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    """Function get_current_user - auto-generated docstring."""
    return decode_token(token)


@router.get("/me", response_model=AuthenticatedUser)
def get_current_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Function get_current_user_info - auto-generated docstring."""
    return current_user
