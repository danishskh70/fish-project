from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.models.trip import Trip
from app.schemas.trip import TripCreate


def create_trip(db: Session, trip_data: TripCreate) -> Trip:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == trip_data.supplier_id
        )
    )

    if supplier is None:
        raise ValueError("Supplier not found.")

    if not supplier.is_active:
        raise ValueError("Cannot create a trip with an inactive supplier.")

    trip = Trip(
        trip_date=trip_data.trip_date,
        supplier_id=trip_data.supplier_id,
        status="PLANNING",
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip


def list_trips(db: Session) -> list[Trip]:
    statement = select(Trip).order_by(
        Trip.trip_date.desc(),
        Trip.id.desc(),
    )
    return list(db.scalars(statement).all())


def get_trip(db: Session, trip_id: int) -> Trip | None:
    return db.get(Trip, trip_id)