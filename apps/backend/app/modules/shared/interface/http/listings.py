"""General listings router compatibility shim."""

from fastapi import APIRouter

router = APIRouter(prefix="/listings", tags=["listings"])
