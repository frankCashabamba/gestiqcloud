from fastapi import APIRouter

from .analysis import router as analysis_router

router = APIRouter()
router.include_router(analysis_router)

__all__ = ["router"]
