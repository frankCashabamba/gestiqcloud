from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Producto:
    id: Optional[int]
    nombre: str
    precio: float
    activo: bool
    tenant_id: int  # tenant scope

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("nombre requerido")
        if self.price < 0:
            raise ValueError("precio no puede ser negativo")
