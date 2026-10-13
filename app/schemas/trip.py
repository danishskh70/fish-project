
from datetime import date, datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field

PositiveFishTypeId = Annotated[int, Field(gt=0)]

class TripCreate(BaseModel):
    trip_date: date
    supplier_id: int = Field(gt=0)
    fish_type_ids: list[PositiveFishTypeId] = Field(min_length=1)
class TripFishTypeAdd(BaseModel):
    fish_type_id: PositiveFishTypeId

class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_date: date
    supplier_id: int
    status: str
    created_at: datetime
