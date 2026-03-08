from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClienteIn:
    nombre: str
    identificacion: str | None = None
    identificacion_tipo: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    is_wholesale: bool = False


@dataclass
class ClienteOut:
    id: int
    nombre: str
    identificacion: str | None = None
    identificacion_tipo: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    is_wholesale: bool = False
