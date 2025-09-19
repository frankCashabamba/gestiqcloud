from datetime import date
from pydantic import BaseModel, ConfigDict


class VacacionOut(BaseModel):
    id: int
    usuario_id: int
    inicio: date
    fin: date
    estado: str | None = None

    model_config = ConfigDict(from_attributes=True)
