from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cliente:
    id: int | None
    nombre: str
    identificacion: str | None
    email: str | None
    telefono: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None
    codigo_postal: str | None
    tenant_id: int

    def validate(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValueError("nombre requerido")
