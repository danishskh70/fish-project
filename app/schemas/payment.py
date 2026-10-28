from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    reference: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["CASH", "ONLINE"]
    kind: Literal["ADVANCE", "PAYMENT"] = "PAYMENT"
    paid_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_customer_id: int
    reference: str
    amount: Decimal
    method: str
    kind: str
    paid_at: datetime
    note: str | None
    created_at: datetime


class PaymentSummaryCustomerRead(BaseModel):
    trip_customer_id: int
    customer_id: int
    billed_amount: Decimal
    complete: bool
    advance_paid: Decimal
    cash_paid: Decimal
    online_paid: Decimal
    total_paid: Decimal
    remaining: Decimal


class PaymentSummaryRead(BaseModel):
    trip_id: int
    customers: list[PaymentSummaryCustomerRead]
    billed_amount: Decimal
    complete: bool
    advance_paid: Decimal
    cash_paid: Decimal
    online_paid: Decimal
    total_paid: Decimal
    outstanding: Decimal
    credit: Decimal
