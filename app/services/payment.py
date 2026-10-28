from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.trip_customer import TripCustomer
from app.schemas.payment import (
    PaymentCreate,
    PaymentRead,
    PaymentSummaryCustomerRead,
    PaymentSummaryRead,
)
from app.services.bill import get_bill

CENTS = Decimal("0.01")
ZERO = Decimal(0)


def _require_trip_customer(
    db: Session, trip_id: int, trip_customer_id: int
) -> TripCustomer:
    trip_customer = db.scalar(
        select(TripCustomer).where(
            TripCustomer.id == trip_customer_id,
            TripCustomer.trip_id == trip_id,
        )
    )
    if trip_customer is None:
        raise LookupError("Trip customer not found for this trip.")
    return trip_customer


def _find_by_reference(db: Session, reference: str) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.reference == reference))


def _replay(
    existing: Payment, trip_customer_id: int, data: PaymentCreate
) -> PaymentRead:
    """Same reference seen before. Same data -> return it. Else conflict."""
    if (
        existing.trip_customer_id != trip_customer_id
        or Decimal(str(existing.amount)) != data.amount
        or existing.method != data.method
        or existing.kind != data.kind
    ):
        raise RuntimeError("Payment reference already used with different data.")
    return PaymentRead.model_validate(existing)


def record_payment(
    db: Session,
    trip_id: int,
    trip_customer_id: int,
    data: PaymentCreate,
) -> tuple[PaymentRead, bool]:
    """Returns (payment, created). created=False means idempotent replay.

    No trip status check: payments are allowed after trip close.
    """
    _require_trip_customer(db, trip_id, trip_customer_id)

    existing = _find_by_reference(db, data.reference)
    if existing is not None:
        return _replay(existing, trip_customer_id, data), False

    try:
        values = {
            "trip_customer_id": trip_customer_id,
            "reference": data.reference,
            "amount": data.amount,
            "method": data.method,
            "kind": data.kind,
            "note": data.note,
        }
        if data.paid_at is not None:
            values["paid_at"] = data.paid_at

        payment = Payment(**values)
        db.add(payment)
        db.flush()
        db.refresh(payment)
        result = PaymentRead.model_validate(payment)
        db.commit()
        return result, True
    except IntegrityError:
        db.rollback()
        # Double tap race: other request won the unique reference.
        existing = _find_by_reference(db, data.reference)
        if existing is None:
            raise
        return _replay(existing, trip_customer_id, data), False
    except Exception:
        db.rollback()
        raise


def list_payments(
    db: Session, trip_id: int, trip_customer_id: int
) -> list[PaymentRead]:
    _require_trip_customer(db, trip_id, trip_customer_id)
    rows = db.scalars(
        select(Payment)
        .where(Payment.trip_customer_id == trip_customer_id)
        .order_by(Payment.id)
    ).all()
    return [PaymentRead.model_validate(row) for row in rows]


def get_payment_summary(db: Session, trip_id: int) -> PaymentSummaryRead:
    bill = get_bill(db, trip_id)  # raises LookupError if trip missing
    billed = {c.trip_customer_id: c for c in bill.customers}

    rows = db.execute(
        select(
            TripCustomer.id,
            TripCustomer.customer_id,
            Payment.method,
            Payment.kind,
            func.sum(Payment.amount),
        )
        .join(Payment, Payment.trip_customer_id == TripCustomer.id)
        .where(TripCustomer.trip_id == trip_id)
        .group_by(
            TripCustomer.id, TripCustomer.customer_id, Payment.method, Payment.kind
        )
    ).all()

    paid: dict[int, dict] = {}
    for trip_customer_id, customer_id, method, kind, total in rows:
        entry = paid.setdefault(
            trip_customer_id,
            {"customer_id": customer_id, "cash": ZERO, "online": ZERO, "advance": ZERO},
        )
        amount = Decimal(str(total))
        if method == "CASH":
            entry["cash"] += amount
        else:
            entry["online"] += amount
        if kind == "ADVANCE":
            entry["advance"] += amount

    customers: list[PaymentSummaryCustomerRead] = []
    for trip_customer_id in sorted(set(billed) | set(paid)):
        bill_row = billed.get(trip_customer_id)
        entry = paid.get(
            trip_customer_id,
            {"customer_id": None, "cash": ZERO, "online": ZERO, "advance": ZERO},
        )
        customer_id = bill_row.customer_id if bill_row else entry["customer_id"]
        billed_amount = bill_row.total_amount if bill_row else ZERO
        total_paid = entry["cash"] + entry["online"]
        customers.append(
            PaymentSummaryCustomerRead(
                trip_customer_id=trip_customer_id,
                customer_id=customer_id,
                billed_amount=billed_amount.quantize(CENTS),
                complete=bill_row.complete if bill_row else True,
                advance_paid=entry["advance"].quantize(CENTS),
                cash_paid=entry["cash"].quantize(CENTS),
                online_paid=entry["online"].quantize(CENTS),
                total_paid=total_paid.quantize(CENTS),
                remaining=(billed_amount - total_paid).quantize(CENTS),
            )
        )

    def total_of(field: str) -> Decimal:
        return sum((getattr(c, field) for c in customers), ZERO).quantize(CENTS)

    outstanding = sum((c.remaining for c in customers if c.remaining > 0), ZERO)
    credit = sum((-c.remaining for c in customers if c.remaining < 0), ZERO)

    return PaymentSummaryRead(
        trip_id=trip_id,
        customers=customers,
        billed_amount=bill.total_amount,
        complete=bill.complete,
        advance_paid=total_of("advance_paid"),
        cash_paid=total_of("cash_paid"),
        online_paid=total_of("online_paid"),
        total_paid=total_of("total_paid"),
        outstanding=outstanding.quantize(CENTS),
        credit=credit.quantize(CENTS),
    )
