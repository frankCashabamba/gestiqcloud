from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Producto:
    id: Optional[int]
    nombre: str
    precio: float
    activo: bool
    empresa_id: int  # tenant scope

    def validate(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValueError("nombre requerido")
        if self.precio < 0:
            raise ValueError("precio no puede ser negativo")

