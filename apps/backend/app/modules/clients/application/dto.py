from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClienteIn:
    nombre: str
    identificacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None


@dataclass
class ClienteOut:
    id: int
    nombre: str
    identificacion: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    localidad: Optional[str]
    provincia: Optional[str]
    pais: Optional[str]
    codigo_postal: Optional[str]
