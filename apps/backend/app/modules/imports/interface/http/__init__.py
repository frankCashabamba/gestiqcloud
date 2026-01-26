from __future__ import annotations

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
    "analyze_router",
    "confirm_router",
    "feedback_router",
    "metrics_router",
    "ocr_router",
    "tenant_router",
]
