from fastapi import APIRouter
from typing import List

router = APIRouter()

USUARIOS: List[dict] = []


@router.get("")
def list_usuarios():
    return USUARIOS
