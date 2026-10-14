
from pydantic import BaseModel, ConfigDict, Field


class RequirementsTableFishType(BaseModel):
    id: int
    name: str


class RequirementsTableQuantity(BaseModel):
    fish_type_id: int
    quantity_bags: int = Field(ge=0)


class RequirementsTableCustomer(BaseModel):
    trip_customer_id: int
    customer_id: int
    name: str
    phone: str
    address: str
    quantities: list[RequirementsTableQuantity]
    total_bags: int = Field(ge=0)


class RequirementsTableFishTotal(BaseModel):
    fish_type_id: int
    quantity_bags: int = Field(ge=0)
    planned_quantity_bags: int | None = Field(default=None, ge=0)
    effective_planned_quantity_bags: int = Field(ge=0)
    shortfall_bags: int = Field(ge=0)
    shortfall_exists: bool


class TripRequirementsTableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trip_id: int
    fish_types: list[RequirementsTableFishType]
    customers: list[RequirementsTableCustomer]
    fish_totals: list[RequirementsTableFishTotal]
    grand_total_bags: int = Field(ge=0)
