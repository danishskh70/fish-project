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

class SameTripCopyError(Exception):
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


def copy_customers_from_trip(
    db: Session,
    destination_trip_id: int,
    source_trip_id: int,
) -> list[TripCustomer]:
    destination_trip = db.get(Trip, destination_trip_id)
    if destination_trip is None:
        raise TripNotFoundError

    source_trip = db.get(Trip, source_trip_id)
    if source_trip is None:
        raise TripNotFoundError

    if destination_trip_id == source_trip_id:
        raise SameTripCopyError

    source_assignments = list(
        db.scalars(
            select(TripCustomer)
            .join(Customer, Customer.id == TripCustomer.customer_id)
            .where(
                TripCustomer.trip_id == source_trip_id,
                Customer.is_active.is_(True),
            )
            .order_by(TripCustomer.id)
        ).all()
    )

    destination_customer_ids = set(
        db.scalars(
            select(TripCustomer.customer_id).where(
                TripCustomer.trip_id == destination_trip_id
            )
        ).all()
    )

    for source_assignment in source_assignments:
        if source_assignment.customer_id in destination_customer_ids:
            continue

        db.add(
            TripCustomer(
                trip_id=destination_trip_id,
                customer_id=source_assignment.customer_id,
            )
        )
        destination_customer_ids.add(source_assignment.customer_id)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return list_trip_customers(db, destination_trip_id)
