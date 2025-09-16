"""Module: configuracion.py

Auto-generated module docstring."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class CategoriaEmpresaBase(BaseModel):
    """ Class CategoriaEmpresaBase - auto-generated docstring. """
    nombre: str

class CategoriaEmpresaCreate(CategoriaEmpresaBase):
    """ Class CategoriaEmpresaCreate - auto-generated docstring. """
    pass


class CategoriaEmpresa(CategoriaEmpresaBase):
    """ Class CategoriaEmpresa - auto-generated docstring. """
    id: int
    class Config:
        """ Class Config - auto-generated docstring. """
        from_attributes = True




#para roles
class RolBaseBase(BaseModel):
    """ Class RolBaseBase - auto-generated docstring. """
    nombre: str
    descripcion: Optional[str] = ""
    permisos: List[str] = []

class RolBaseCreate(RolBaseBase):
    """ Class RolBaseCreate - auto-generated docstring. """
    pass

class RolBaseUpdate(RolBaseBase):
    """ Class RolBaseUpdate - auto-generated docstring. """
    permisos: List[str]

class RolBase(RolBaseBase):
    """ Class RolBase - auto-generated docstring. """
    id: int
    class Config:
        """ Class Config - auto-generated docstring. """
        from_attributes = True


class PermisoAccionGlobalpermiso(BaseModel):
    """ Class PermisoAccionGlobalpermiso - auto-generated docstring. """
    id: int
    clave: str
    descripcion: Optional[str]
    class Config:
        """ Class Config - auto-generated docstring. """
        from_attributes = True




class AuthenticatedUser(BaseModel):
    """ Class AuthenticatedUser - auto-generated docstring. """
    user_id: int
    is_superadmin: bool
    user_type: str
    empresa_id: Optional[int] = None
    empresa_slug: Optional[str] = None
    plantilla: Optional[str] = None
    es_admin_empresa: Optional[bool] = None
    permisos: Optional[Dict] = {}
    nombre: Optional[str] = None

    class Config:
        """ Class Config - auto-generated docstring. """
        extra = "ignore"