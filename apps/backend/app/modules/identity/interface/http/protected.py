"""Protected routes and authentication utilities.

`get_current_user` aquí devuelve un `AuthenticatedUser` (schema Pydantic) para
los routers que lo esperan, pero **NO** decodifica el token por su cuenta: usa
`with_access_claims` (la única puerta de validación de token del backend) y solo
mapea los claims al schema. Ver `docs/security/auth-contract.md`.
"""

from fastapi import APIRouter, Depends, Request

from app.core.access_guard import with_access_claims
from app.schemas.configuracion import AuthenticatedUser

router = APIRouter(prefix="/protected", tags=["protected"])


def _claims_to_user(payload: dict) -> AuthenticatedUser:
    """Mapea el dict de claims (ya validado por with_access_claims) a AuthenticatedUser."""
    kind = payload.get("kind") or payload.get("scope") or "tenant"
    user_type = "admin" if kind == "admin" else "tenant"
    return AuthenticatedUser(
        user_id=payload.get("user_id"),
        is_superadmin=bool(payload.get("is_superadmin") or False),
        user_type=user_type,
        tenant_id=payload.get("tenant_id"),
        empresa_slug=payload.get("empresa_slug"),
        plantilla=payload.get("plantilla"),
        is_company_admin=payload.get("is_company_admin"),
        permisos=payload.get("permisos") or payload.get("permissions") or {},
        name=payload.get("nombre") or payload.get("name"),
    )


def get_current_user(request: Request) -> AuthenticatedUser:
    """Usuario autenticado como AuthenticatedUser, validado vía with_access_claims."""
    claims = with_access_claims(request)
    return _claims_to_user(claims)


@router.get("/me", response_model=AuthenticatedUser)
def get_current_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get current user information."""
    return current_user
