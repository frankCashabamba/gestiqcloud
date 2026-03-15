"""POS — Router principal (orquestador).

Este módulo solo agrega los sub-routers especializados. Toda la lógica de
negocio vive en los módulos individuales:

  registers.py  — cajas / terminales
  shifts.py     — turnos y arqueos
  receipts.py   — tickets, checkout, devoluciones
  analytics.py  — márgenes por producto / cliente
  daily_counts.py — reportes diarios de caja
  numbering.py  — contadores y series de numeración
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from . import analytics, daily_counts, numbering, receipts, registers, shifts

# Router raíz sin prefijo — cada sub-router lleva su propio prefix="/pos".
router = APIRouter()

router.include_router(registers.router)
router.include_router(shifts.router)
router.include_router(receipts.router)
router.include_router(analytics.router)
router.include_router(daily_counts.router)
router.include_router(numbering.router)


# ---------------------------------------------------------------------------
# Health check (no requiere autenticación)
# ---------------------------------------------------------------------------

_health_router = APIRouter(prefix="/pos", tags=["POS"])


@_health_router.get("/health", include_in_schema=False)
def health_check():
    return {
        "status": "healthy",
        "module": "pos",
        "timestamp": datetime.utcnow().isoformat(),
    }


router.include_router(_health_router)
