from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.handover import Handover, HandoverLine
from app.models.trip import Trip
from app.models.trip_customer import TripCustomer
from app.schemas.bill import BillCustomerRead, BillRead

CENTS = Decimal("0.01")


def get_bill(db: Session, trip_id: int) -> BillRead:
    if db.get(Trip, trip_id) is None:
        raise LookupError("Trip not found.")

    rows = db.execute(
        select(
            TripCustomer.id,
            TripCustomer.customer_id,
            HandoverLine.bags,
            HandoverLine.rate_per_bag,
        )
        .join(Handover, Handover.trip_customer_id == TripCustomer.id)
        .join(HandoverLine, HandoverLine.handover_id == Handover.id)
        .where(TripCustomer.trip_id == trip_id)
        .order_by(TripCustomer.id)
    ).all()

    # trip_customer_id -> [customer_id, bags, unpriced_bags, amount]
    per_customer: dict[int, list] = {}
    for trip_customer_id, customer_id, bags, rate in rows:
        entry = per_customer.setdefault(
            trip_customer_id, [customer_id, 0, 0, Decimal(0)]
        )
        entry[1] += bags
        if rate is None:
            entry[2] += bags
        else:
            entry[3] += bags * Decimal(str(rate))

    customers = [
        BillCustomerRead(
            trip_customer_id=trip_customer_id,
            customer_id=customer_id,
            total_bags=bags,
            unpriced_bags=unpriced,
            total_amount=amount.quantize(CENTS),
            complete=unpriced == 0,
        )
        for trip_customer_id, (customer_id, bags, unpriced, amount)
        in per_customer.items()
    ]

    total_unpriced = sum(c.unpriced_bags for c in customers)
    total_amount = sum((c.total_amount for c in customers), Decimal(0))
    return BillRead(
        trip_id=trip_id,
        customers=customers,
        total_bags=sum(c.total_bags for c in customers),
        unpriced_bags=total_unpriced,
        total_amount=total_amount.quantize(CENTS),
        complete=total_unpriced == 0,
    )