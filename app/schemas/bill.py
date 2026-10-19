from decimal import Decimal

from pydantic import BaseModel


class BillCustomerRead(BaseModel):
    trip_customer_id: int
    customer_id: int
    total_bags: int
    unpriced_bags: int
    total_amount: Decimal
    complete: bool


class BillRead(BaseModel):
    trip_id: int
    customers: list[BillCustomerRead]
    total_bags: int
    unpriced_bags: int
    total_amount: Decimal
    complete: bool