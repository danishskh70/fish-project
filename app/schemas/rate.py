from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class RateLineCreate(BaseModel):
    fish_type_id: int = Field(gt=0)
    rate_per_bag: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class RatesSet(BaseModel):
    rates: list[RateLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_fish_types(self):
        ids = [line.fish_type_id for line in self.rates]
        if len(ids) != len(set(ids)):
            raise ValueError("Each fish type must appear only once.")
        return self


class RateSetRead(BaseModel):
    fish_type_id: int
    rate_set: bool


class RateStatusRead(BaseModel):
    fish_type_id: int
    fish_type_name: str
    default_set: bool
    override_trip_customer_ids: list[int]