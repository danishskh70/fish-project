from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class SupplierDeliveryItemCreate(BaseModel):
    fish_type_id: int = Field(gt=0)
    delivered_bags: int = Field(ge=0)
    rejected_bags: int = Field(default=0, ge=0)
    damaged_bags: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_received_quantities(self):
        if self.rejected_bags + self.damaged_bags > self.delivered_bags:
            raise ValueError(
                "Rejected and damaged bags cannot exceed delivered bags."
            )
        return self


class SupplierDeliveryCreate(BaseModel):
    items: list[SupplierDeliveryItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_fish_types(self):
        ids = [item.fish_type_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each fish type must appear only once.")
        return self


class SupplierDeliveryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fish_type_id: int
    fish_type_name: str
    planned_bags: int
    delivered_bags: int
    rejected_bags: int
    damaged_bags: int

    @computed_field
    @property
    def accepted_bags(self) -> int:
        return self.delivered_bags - self.rejected_bags - self.damaged_bags

    @computed_field
    @property
    def shortage_bags(self) -> int:
        return max(self.planned_bags - self.delivered_bags, 0)

    @computed_field
    @property
    def excess_bags(self) -> int:
        return max(self.delivered_bags - self.planned_bags, 0)


class SupplierDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_list_id: int
    received_at: datetime
    items: list[SupplierDeliveryItemRead]
