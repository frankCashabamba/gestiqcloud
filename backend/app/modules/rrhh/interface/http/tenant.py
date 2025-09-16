from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import VacacionRepo
from .schemas import VacacionOut

router = APIRouter()


@router.get("/vacaciones", response_model=list[VacacionOut])
def list_vacaciones(db: Session = Depends(get_db)):
    return VacacionRepo(db).list()
