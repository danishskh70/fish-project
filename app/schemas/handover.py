from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


class HandoverLineCreate(BaseModel):
    fish_type_id: int = Field(gt=0)
    bags: int = Field(ge=0)


class HandoverCreate(BaseModel):
    trip_customer_id: int = Field(gt=0)
    submit_reference: str = Field(min_length=1, max_length=64)
    handed_over_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)
    lines: list[HandoverLineCreate] = Field(min_length=1)

    @field_validator("submit_reference")
    @classmethod
    def strip_reference(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Submit reference cannot be blank.")
        return value

    @model_validator(mode="after")
    def validate_unique_fish_types(self):
        ids = [line.fish_type_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("Each fish type must appear only once.")
        return self


class HandoverLineRead(BaseModel):
    fish_type_id: int
    fish_type_name: str
    bags: int


class HandoverRead(BaseModel):
    id: int
    trip_id: int
    trip_customer_id: int
    customer_id: int
    submit_reference: str
    handed_over_at: datetime
    note: str | None
    created_at: datetime
    lines: list[HandoverLineRead]

    @computed_field
    @property
    def total_bags(self) -> int:
        return sum(line.bags for line in self.lines)


class StockLineRead(BaseModel):
    fish_type_id: int
    fish_type_name: str
    on_slip: bool
    slip_bags: int
    rejected_bags: int  # info only
    damaged_bags: int  # info only
    handed_bags: int

    @computed_field
    @property
    def left_bags(self) -> int:
        # S5 will also subtract dam bags. Not here.
        return self.slip_bags - self.handed_bags

    @computed_field
    @property
    def over_slip(self) -> bool:
        return self.handed_bags > self.slip_bags


class CustomerTotalRead(BaseModel):
    trip_customer_id: int
    customer_id: int
    fish_type_id: int
    fish_type_name: str
    bags: int