
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.supplier import Supplier
from app.models.trip import Trip
from app.models.trip_fish_type import TripFishType
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

    fish_types = list(
        db.scalars(
            select(FishType).where(
                FishType.id.in_(trip_data.fish_type_ids)
            )
        ).all()
    )

    fish_types_by_id = {
        fish_type.id: fish_type
        for fish_type in fish_types
    }

    for fish_type_id in trip_data.fish_type_ids:
        fish_type = fish_types_by_id.get(fish_type_id)

        if fish_type is None:
            raise ValueError(
                f"Fish type {fish_type_id} not found."
            )

        if not fish_type.is_active:
            raise ValueError(
                f"Cannot add inactive fish type {fish_type_id} to a trip."
            )

    trip = Trip(
        trip_date=trip_data.trip_date,
        supplier_id=trip_data.supplier_id,
        status="PLANNING",
    )

    db.add(trip)

    try:
        db.flush()

        db.add_all(
            [
                TripFishType(
                    trip_id=trip.id,
                    fish_type_id=fish_type_id,
                )
                for fish_type_id in trip_data.fish_type_ids
            ]
        )

        db.commit()
        db.refresh(trip)

    except Exception:
        db.rollback()
        raise

    return trip


def list_trips(db: Session) -> list[Trip]:
    statement = select(Trip).order_by(
        Trip.trip_date.desc(),
        Trip.id.desc(),
    )
    return list(db.scalars(statement).all())


def get_trip(db: Session, trip_id: int) -> Trip | None:
    return db.get(Trip, trip_id)

def add_fish_type_to_trip(
    db: Session,
    trip_id: int,
    fish_type_id: int,
) -> TripFishType:
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise ValueError("Trip not found.")

    fish_type = db.get(FishType, fish_type_id)

    if fish_type is None:
        raise ValueError("Fish type not found.")

    if not fish_type.is_active:
        raise ValueError("Cannot add an inactive fish type to a trip.")

    existing_association = db.scalar(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id == fish_type_id,
        )
    )

    if existing_association is not None:
        raise ValueError("Fish type is already configured for this trip.")

    association = TripFishType(
        trip_id=trip_id,
        fish_type_id=fish_type_id,
    )

    db.add(association)

    try:
        db.commit()
        db.refresh(association)
    except Exception:
        db.rollback()
        raise

    return association