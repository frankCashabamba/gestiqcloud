from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Cliente:
    id: Optional[int]
    nombre: str
    identificacion: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    localidad: Optional[str]
    provincia: Optional[str]
    pais: Optional[str]
    codigo_postal: Optional[str]
    empresa_id: int

    def validate(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValueError("nombre requerido")

