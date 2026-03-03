"""
Minimal, declarative-first importer (v2).

Objetivo: flujo simple de ingestión sin legacy ni múltiples rutas.
"""

from .router import router  # re-export for FastAPI include_router_safe
