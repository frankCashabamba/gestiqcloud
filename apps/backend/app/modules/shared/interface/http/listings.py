"""General listings router - provides common listing endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/listings", tags=["listings"])
