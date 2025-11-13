from fastapi import APIRouter

router = APIRouter()

USUARIOS: list[dict] = []


@router.get("")
def list_usuarios():
    return USUARIOS
