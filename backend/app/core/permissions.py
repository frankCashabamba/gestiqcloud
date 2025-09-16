"""Module: permissions.py

Auto-generated module docstring."""

from fastapi import HTTPException


def validar_acceso_empresa(empresa_id: int, current_user):
    """ Function validar_acceso_empresa - auto-generated docstring. """
    if not current_user.is_superadmin and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
