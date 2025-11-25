from datetime import date

from pydantic import BaseModel, ConfigDict


class VacationOut(BaseModel):
    id: int
    user_id: int
    start_date: date
    end_date: date
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)
