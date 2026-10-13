from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TripCreate(BaseModel):
    trip_date: date
    supplier_id: int = Field(gt=0)


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_date: date
    supplier_id: int
    status: str
    created_at: datetime