from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import CajaRepo, BancoRepo
from .schemas import MovimientoOut

router = APIRouter()


@router.get("/caja/movimientos", response_model=list[MovimientoOut])
def list_caja(db: Session = Depends(get_db)):
    return CajaRepo(db).list()


@router.get("/bancos/movimientos", response_model=list[MovimientoOut])
def list_bancos(db: Session = Depends(get_db)):
    return BancoRepo(db).list()
