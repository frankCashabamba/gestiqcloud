"""Router for tenant user management."""
from fastapi import APIRouter

router = APIRouter()

USERS: list[dict] = []


@router.get("")
def list_users():
    """List all users."""
    return USERS
