from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.trip import Trip
from app.models.trip_customer import TripCustomer
from app.schemas.trip_customer import TripCustomerCreate


class TripNotFoundError(Exception):
    pass


class CustomerNotFoundError(Exception):
    pass


class InactiveCustomerError(Exception):
    pass


class DuplicateTripCustomerError(Exception):
    pass


def add_customer_to_trip(
    db: Session,
    trip_id: int,
    data: TripCustomerCreate,
) -> TripCustomer:
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise TripNotFoundError

    customer = db.get(Customer, data.customer_id)

    if customer is None:
        raise CustomerNotFoundError

    if not customer.is_active:
        raise InactiveCustomerError

    existing_assignment = db.scalar(
        select(TripCustomer).where(
            TripCustomer.trip_id == trip_id,
            TripCustomer.customer_id == data.customer_id,
        )
    )

    if existing_assignment is not None:
        raise DuplicateTripCustomerError

    assignment = TripCustomer(
        trip_id=trip_id,
        customer_id=data.customer_id,
    )

    db.add(assignment)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        # Protect against a duplicate created concurrently.
        existing_assignment = db.scalar(
            select(TripCustomer).where(
                TripCustomer.trip_id == trip_id,
                TripCustomer.customer_id == data.customer_id,
            )
        )

        if existing_assignment is not None:
            raise DuplicateTripCustomerError from exc

        raise

    db.refresh(assignment)
    return assignment


def list_trip_customers(
    db: Session,
    trip_id: int,
) -> list[TripCustomer]:
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise TripNotFoundError

    statement = (
        select(TripCustomer)
        .where(TripCustomer.trip_id == trip_id)
        .order_by(TripCustomer.id)
    )

    return list(db.scalars(statement).all())
