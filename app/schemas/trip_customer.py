from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TripCustomerCreate(BaseModel):
    customer_id: int = Field(gt=0)


class TripCustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    customer_id: int
    created_at: datetime
