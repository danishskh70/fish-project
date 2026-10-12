from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


SupplierName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

SupplierPhone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]

SupplierAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class SupplierCreate(BaseModel):
    name: SupplierName
    phone: SupplierPhone
    address: SupplierAddress


class SupplierUpdate(BaseModel):
    name: SupplierName | None = None
    phone: SupplierPhone | None = None
    address: SupplierAddress | None = None


class SupplierRead(BaseModel):
    id: int
    name: str
    phone: str
    address: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)