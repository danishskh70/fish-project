from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.handover import Handover, HandoverLine
from app.models.payment import Payment
from app.models.trip_customer import TripCustomer
from app.schemas.payment import (
    PaymentCreate,
    PaymentRead,
    PaymentSummaryCustomerRead,
    PaymentSummaryRead,
    PaymentVoid,
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


def void_payment(
    db: Session,
    trip_id: int,
    trip_customer_id: int,
    payment_id: int,
    data: PaymentVoid,
) -> PaymentRead:
    """Cancel a payment. Row stays. Allowed after trip close. Once only."""
    _require_trip_customer(db, trip_id, trip_customer_id)

    payment = db.scalar(
        select(Payment)
        .where(
            Payment.id == payment_id,
            Payment.trip_customer_id == trip_customer_id,
        )
        .with_for_update()
    )
    if payment is None:
        raise LookupError("Payment not found for this customer.")
    if payment.voided_at is not None:
        raise RuntimeError("Payment already voided.")

    try:
        payment.voided_at = datetime.now(UTC)
        payment.void_reason = data.reason
        db.flush()
        db.refresh(payment)
        result = PaymentRead.model_validate(payment)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def list_payments(
    db: Session, trip_id: int, trip_customer_id: int
) -> list[PaymentRead]:
    """All rows, voided included."""
    _require_trip_customer(db, trip_id, trip_customer_id)
    rows = db.scalars(
        select(Payment)
        .where(Payment.trip_customer_id == trip_customer_id)
        .order_by(Payment.id)
    ).all()
    return [PaymentRead.model_validate(row) for row in rows]


def _previous_balances(
    db: Session, trip_id: int, customer_ids: set[int]
) -> dict[int, tuple[Decimal, bool]]:
    """customer_id -> (old balance, complete). Earlier trips = lower trip id.

    Balance = priced bill minus non-voided payments. Computed, never stored.
    complete=False when an earlier trip still has unpriced bags.
    """
    if not customer_ids:
        return {}

    billed_rows = db.execute(
        select(
            TripCustomer.customer_id,
            func.sum(HandoverLine.bags * HandoverLine.rate_per_bag),
            func.sum(
                case((HandoverLine.rate_per_bag.is_(None), HandoverLine.bags), else_=0)
            ),
        )
        .join(Handover, Handover.trip_customer_id == TripCustomer.id)
        .join(HandoverLine, HandoverLine.handover_id == Handover.id)
        .where(
            TripCustomer.trip_id < trip_id,
            TripCustomer.customer_id.in_(customer_ids),
        )
        .group_by(TripCustomer.customer_id)
    ).all()

    paid_rows = db.execute(
        select(TripCustomer.customer_id, func.sum(Payment.amount))
        .join(Payment, Payment.trip_customer_id == TripCustomer.id)
        .where(
            TripCustomer.trip_id < trip_id,
            TripCustomer.customer_id.in_(customer_ids),
            Payment.voided_at.is_(None),
        )
        .group_by(TripCustomer.customer_id)
    ).all()

    billed = {
        customer_id: (Decimal(str(total or 0)), int(unpriced or 0))
        for customer_id, total, unpriced in billed_rows
    }
    paid = {customer_id: Decimal(str(total or 0)) for customer_id, total in paid_rows}

    result: dict[int, tuple[Decimal, bool]] = {}
    for customer_id in customer_ids:
        billed_amount, unpriced = billed.get(customer_id, (ZERO, 0))
        balance = billed_amount - paid.get(customer_id, ZERO)
        result[customer_id] = (balance.quantize(CENTS), unpriced == 0)
    return result


def get_payment_summary(db: Session, trip_id: int) -> PaymentSummaryRead:
    bill = get_bill(db, trip_id)  # raises LookupError if trip missing
    billed = {c.trip_customer_id: c for c in bill.customers}

    trip_customers = db.execute(
        select(TripCustomer.id, TripCustomer.customer_id)
        .where(TripCustomer.trip_id == trip_id)
        .order_by(TripCustomer.id)
    ).all()

    rows = db.execute(
        select(
            Payment.trip_customer_id,
            Payment.method,
            Payment.kind,
            func.sum(Payment.amount),
        )
        .join(TripCustomer, TripCustomer.id == Payment.trip_customer_id)
        .where(TripCustomer.trip_id == trip_id, Payment.voided_at.is_(None))
        .group_by(Payment.trip_customer_id, Payment.method, Payment.kind)
    ).all()

    paid: dict[int, dict[str, Decimal]] = {}
    for trip_customer_id, method, kind, total in rows:
        entry = paid.setdefault(
            trip_customer_id, {"cash": ZERO, "online": ZERO, "advance": ZERO}
        )
        amount = Decimal(str(total))
        if method == "CASH":
            entry["cash"] += amount
        else:
            entry["online"] += amount
        if kind == "ADVANCE":
            entry["advance"] += amount

    previous = _previous_balances(
        db, trip_id, {customer_id for _, customer_id in trip_customers}
    )

    customers: list[PaymentSummaryCustomerRead] = []
    for trip_customer_id, customer_id in trip_customers:
        bill_row = billed.get(trip_customer_id)
        entry = paid.get(trip_customer_id, {"cash": ZERO, "online": ZERO, "advance": ZERO})
        billed_amount = bill_row.total_amount if bill_row else ZERO
        total_paid = entry["cash"] + entry["online"]
        remaining = billed_amount - total_paid
        previous_balance, previous_complete = previous[customer_id]
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
                remaining=remaining.quantize(CENTS),
                previous_balance=previous_balance,
                previous_complete=previous_complete,
                total_due=(previous_balance + remaining).quantize(CENTS),
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
