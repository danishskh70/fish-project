from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    model_validator,
)

CustomerName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

CustomerPhone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]

CustomerAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class CustomerCreate(BaseModel):
    name: CustomerName
    phone: CustomerPhone
    address: CustomerAddress


class CustomerUpdate(BaseModel):
    name: CustomerName | None = None
    phone: CustomerPhone | None = None
    address: CustomerAddress | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not any(
            value is not None
            for value in self.model_dump().values()
        ):
            raise ValueError("At least one non-null field must be provided.")
        return self

class CustomerRead(BaseModel):
    id: int
    name: str
    phone: str
    address: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)