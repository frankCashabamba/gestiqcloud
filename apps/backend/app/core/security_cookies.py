"""
Security guards actualizados para usar cookies HttpOnly.
Reemplazo de Authorization header por cookies seguras.
"""
from __future__ import annotations

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.auth_cookies import get_token_from_cookie_or_header
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService


def get_current_user_from_cookie(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Obtiene el usuario actual desde cookie (o header como fallback).
    
    Migración gradual: Acepta token desde cookie (preferido) o Authorization header (legacy).
    
    Raises:
        HTTPException 401: Si no hay token o es inválido
    """
    # 1. Obtener token (cookie o header)
    token = get_token_from_cookie_or_header(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Verificar y decodificar token
    token_service = PyJWTTokenService()
    
    try:
        payload = token_service.decode_access_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Extraer user_id del payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )
    
    # 4. Buscar usuario en DB
    from app.models.empresa.usuarioempresa import UsuarioEmpresa
    
    user = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


def get_current_active_tenant_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Obtiene usuario tenant activo desde cookie.
    
    Uso en routers:
        @router.get("/protected")
        def protected_route(current_user = Depends(get_current_active_tenant_user)):
            return {"user_id": current_user.id}
    """
    user = get_current_user_from_cookie(request, db)
    
    # Validación específica de tenant
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any tenant",
        )
    
    return user


def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Obtiene usuario admin desde cookie.
    
    Verifica que el usuario tenga rol de admin.
    """
    user = get_current_user_from_cookie(request, db)
    
    # Verificar rol admin (ajustar según tu modelo)
    if not getattr(user, "is_admin", False) and not getattr(user, "admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return user


# Alias para compatibilidad con código existente
get_current_user = get_current_user_from_cookie
