from __future__ import annotations

from .ai_health import protected_router as ai_health_protected_router
from .ai_health import router as ai_health_router
from .analyze import router as analyze_router
from .confirm import router as confirm_router
from .feedback import router as feedback_router
from .metrics import router as metrics_router
from .ocr import router as ocr_router
from .preview import files_router, router
from .tenant import public_router
from .tenant import router as tenant_router

# Export routers
__all__ = [
    "router",
    "public_router",
    "files_router",
    "ai_health_router",
    "ai_health_protected_router",
    "analyze_router",
    "confirm_router",
    "feedback_router",
    "metrics_router",
    "ocr_router",
    "tenant_router",
]
