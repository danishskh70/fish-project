from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositiveFishTypeId = Annotated[int, Field(gt=0)]


class PackingListItemCreate(BaseModel):
    fish_type_id: PositiveFishTypeId
    quantity_bags: int = Field(ge=0)


class PackingListCreate(BaseModel):
    items: list[PackingListItemCreate] = Field(min_length=1)


class PackingListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fish_type_id: int
    quantity_bags: int = Field(ge=0)


class PackingListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    created_at: datetime
    items: list[PackingListItemRead]
    total_bags: int = Field(ge=0)

class PackingListItemQuantityUpdate(BaseModel):
    quantity_bags: int = Field(ge=0)
    
class PackingListItemAdd(BaseModel):
    fish_type_id: PositiveFishTypeId
    quantity_bags: int = Field(ge=1)