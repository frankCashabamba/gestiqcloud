from datetime import date
from pydantic import BaseModel


class VacacionOut(BaseModel):
    id: int
    usuario_id: int
    inicio: date
    fin: date
    estado: str | None = None

    class Config:
        from_attributes = True

