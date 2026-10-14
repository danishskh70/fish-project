
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupplierListStatus = Literal["DRAFT", "FINAL", "SUPERSEDED"]


class SupplierListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fish_type_id: int
    fish_type_name: str
    quantity_bags: int = Field(ge=0)
    tub_count: int = Field(ge=0)


class SupplierListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    version_number: int
    status: SupplierListStatus
    created_at: datetime
    finalized_at: datetime | None
    items: list[SupplierListItemRead]
    total_bags: int = Field(ge=0)
    total_tubs: int = Field(ge=0)
