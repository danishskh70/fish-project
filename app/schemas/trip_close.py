from pydantic import BaseModel

from app.schemas.handover import CustomerTotalRead, StockLineRead
from app.schemas.trip import TripRead


class TripCloseRead(BaseModel):
    trip: TripRead
    stock: list[StockLineRead]
    totals: list[CustomerTotalRead]