from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cliente:
    # TODO FASE 2: cambiar id de int a UUID — activo en DB como int por migración legacy
    # El cambio afecta >5 archivos (ports, repositories, use_cases, interface/http, sales, pos,
    # invoicing) y requiere una migración coordinada de columna en BD. Evaluar junto con Zero/PGSync.
    id: int | None
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
    tenant_id: int = 0

    def validate(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValueError("nombre requerido")
