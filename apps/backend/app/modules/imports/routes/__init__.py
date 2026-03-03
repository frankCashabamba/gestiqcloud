from fastapi import APIRouter

from .analysis import router as analysis_router
from .reprocess import router as reprocess_router
from .templates import router as templates_router

router = APIRouter()
router.include_router(analysis_router)
router.include_router(templates_router)
router.include_router(reprocess_router)

__all__ = ["router"]
