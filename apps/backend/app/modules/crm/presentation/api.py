from fastapi import APIRouter

router = APIRouter()


@router.get("/customers")
def list_customers():
    return {"items": [], "total": 0}

