
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TripCustomerRequirementCreate(BaseModel):
    fish_type_id: int = Field(gt=0)
    quantity_bags: int = Field(gt=0)


class TripCustomerRequirementUpdate(BaseModel):
    quantity_bags: int = Field(gt=0)


class TripCustomerRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_customer_id: int
    fish_type_id: int
    quantity_bags: int
    created_at: datetime
