# app/api/v1/me.py
from collections.abc import Mapping
from typing import Any

from app.config.database import get_db
from app.config.settings import settings
from app.core.deps import require_tenant
from app.core.refresh import decode_and_validate
from app.db.rls import ensure_rls
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

router = APIRouter(prefix="/me", tags=["Me"], dependencies=[Depends(ensure_rls)])


# --- Endpoint original para usuarios de empresa (resuelve tenant en servidor) ---
@router.get("/")
def me(s: dict = Depends(require_tenant)) -> dict:
    # Devuelve perfil + permisos (resueltos en servidor)
    return {
        "user_id": s.get("tenant_user_id"),
        "tenant_id": s.get("tenant_id"),
        "permisos": [],
    }


# --- Helper: extraer Bearer del header Authorization ---
def _get_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# --- Compatibilidad FE: lee Access Token y devuelve tenant/user/scope ---
@router.get("/tenant")
def me_tenant(request: Request, db: Session = Depends(get_db)):
    """
    Devuelve tenant y user_id leyendo el Access Token (Bearer).
    - Para 'admin': usa ADMIN_SYSTEM_TENANT_ID.
    - Para 'tenant': intenta usar 'tenant_id' del token. Si no viene, 404.
    """
    token = _get_bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="missing_access_token")

    try:
        payload: Mapping[str, Any] = decode_and_validate(token, expected_type="access")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_access_token")

    kind = (payload.get("kind") or "tenant") if isinstance(payload, dict) else "tenant"
    user_id = (
        str(payload.get("user_id")) if isinstance(payload.get("user_id"), (str, int)) else None
    )

    if kind == "admin":
        # Admin: devolvemos el tenant del sistema
        return {
            "tenant_id": str(settings.ADMIN_SYSTEM_TENANT_ID),
            "user_id": user_id,
            "scope": "admin",
        }

    # Tenant user: idealmente el access token trae tenant_id
    tenant_id = payload.get("tenant_id") if isinstance(payload, dict) else None
    if not tenant_id:
        # Si tus access tokens de tenant aún no incluyen tenant_id,
        # 1) añádelo al generar el access en el login de tenant, o
        # 2) usa GET /api/v1/me (require_tenant) en el FE.
        raise HTTPException(status_code=404, detail="tenant_not_found")

    # Optionally enrich with username and empresa_slug for better UX
    username = None
    empresa_slug = None
    es_admin_empresa = None
    try:
        uid = int(user_id) if user_id and user_id.isdigit() else None
    except Exception:
        uid = None
    if uid is not None:
        u = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.id == uid).first()
        if u is not None:
            username = getattr(u, "username", None)
            try:
                # Get slug from tenant (Empresa no longer exists)
                from app.models.tenant import Tenant

                tenant = (
                    db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
                    if hasattr(u, "tenant_id") and u.tenant_id
                    else None
                )
                empresa_slug = tenant.slug if tenant else None
            except Exception:
                empresa_slug = None
            try:
                es_admin_empresa = bool(getattr(u, "es_admin_empresa", None))
            except Exception:
                es_admin_empresa = None

    return {
        "tenant_id": str(tenant_id),
        "user_id": user_id,
        "username": username,
        "empresa_slug": empresa_slug,
        "es_admin_empresa": es_admin_empresa,
        "scope": "tenant",
    }


# --- Nuevo: endpoint para admin esperado por el FE (/me/admin) ---
@router.get("/admin")
def me_admin(request: Request):
    """
    Perfil admin leyendo el Access Token (Bearer).
    Responde con la forma que espera tu FE: { user_id, is_superadmin?, user_type }.
    """
    token = _get_bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="missing_access_token")

    try:
        payload: Mapping[str, Any] = decode_and_validate(token, expected_type="access")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_access_token")

    kind = (payload.get("kind") or "tenant") if isinstance(payload, dict) else "tenant"
    if kind != "admin":
        raise HTTPException(status_code=403, detail="not_admin")

    user_id = (
        str(payload.get("user_id")) if isinstance(payload.get("user_id"), (str, int)) else None
    )
    is_super = bool(payload.get("is_superadmin") or False)

    return {
        "user_id": user_id,
        "is_superadmin": is_super,
        "user_type": "admin",
    }
