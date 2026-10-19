from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.handover import Handover, HandoverLine
from app.models.trip import Trip
from app.models.trip_customer import TripCustomer
from app.models.trip_customer_rate import TripCustomerRate
from app.models.trip_fish_type import TripFishType
from app.schemas.rate import RateSetRead, RatesSet, RateStatusRead


def _require_trip(db: Session, trip_id: int) -> None:
    if db.get(Trip, trip_id) is None:
        raise LookupError("Trip not found.")


def _trip_fish_rows(
    db: Session,
    trip_id: int,
    fish_type_ids: set[int],
) -> dict[int, TripFishType]:
    rows = db.scalars(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id.in_(fish_type_ids),
        )
    ).all()
    by_fish = {row.fish_type_id: row for row in rows}
    for fish_type_id in fish_type_ids:
        if fish_type_id not in by_fish:
            raise LookupError(
                f"Fish type {fish_type_id} is not configured for this trip."
            )
    return by_fish


def set_trip_rates(
    db: Session,
    trip_id: int,
    data: RatesSet,
) -> list[RateSetRead]:
    _require_trip(db, trip_id)
    rows = _trip_fish_rows(
        db, trip_id, {line.fish_type_id for line in data.rates}
    )

    try:
        for line in data.rates:
            rows[line.fish_type_id].rate_per_bag = line.rate_per_bag

            customers_with_override = select(
                TripCustomerRate.trip_customer_id
            ).where(TripCustomerRate.fish_type_id == line.fish_type_id)
            handover_ids = (
                select(Handover.id)
                .join(
                    TripCustomer,
                    TripCustomer.id == Handover.trip_customer_id,
                )
                .where(
                    TripCustomer.trip_id == trip_id,
                    TripCustomer.id.not_in(customers_with_override),
                )
            )
            db.execute(
                update(HandoverLine)
                .where(
                    HandoverLine.fish_type_id == line.fish_type_id,
                    HandoverLine.rate_per_bag.is_(None),
                    HandoverLine.handover_id.in_(handover_ids),
                )
                .values(rate_per_bag=line.rate_per_bag)
                .execution_options(synchronize_session=False)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [
        RateSetRead(fish_type_id=line.fish_type_id, rate_set=True)
        for line in data.rates
    ]


def set_customer_rates(
    db: Session,
    trip_id: int,
    trip_customer_id: int,
    data: RatesSet,
) -> list[RateSetRead]:
    _require_trip(db, trip_id)
    trip_customer = db.scalar(
        select(TripCustomer).where(
            TripCustomer.id == trip_customer_id,
            TripCustomer.trip_id == trip_id,
        )
    )
    if trip_customer is None:
        raise LookupError("Trip customer not found for this trip.")
    _trip_fish_rows(db, trip_id, {line.fish_type_id for line in data.rates})

    try:
        for line in data.rates:
            existing = db.scalar(
                select(TripCustomerRate).where(
                    TripCustomerRate.trip_customer_id == trip_customer.id,
                    TripCustomerRate.fish_type_id == line.fish_type_id,
                )
            )
            if existing is None:
                db.add(
                    TripCustomerRate(
                        trip_customer_id=trip_customer.id,
                        fish_type_id=line.fish_type_id,
                        rate_per_bag=line.rate_per_bag,
                    )
                )
            else:
                existing.rate_per_bag = line.rate_per_bag

            handover_ids = select(Handover.id).where(
                Handover.trip_customer_id == trip_customer.id
            )
            db.execute(
                update(HandoverLine)
                .where(
                    HandoverLine.fish_type_id == line.fish_type_id,
                    HandoverLine.rate_per_bag.is_(None),
                    HandoverLine.handover_id.in_(handover_ids),
                )
                .values(rate_per_bag=line.rate_per_bag)
                .execution_options(synchronize_session=False)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [
        RateSetRead(fish_type_id=line.fish_type_id, rate_set=True)
        for line in data.rates
    ]


def get_rate_status(db: Session, trip_id: int) -> list[RateStatusRead]:
    _require_trip(db, trip_id)

    fish_rows = db.execute(
        select(TripFishType, FishType.name)
        .join(FishType, FishType.id == TripFishType.fish_type_id)
        .where(TripFishType.trip_id == trip_id)
        .order_by(TripFishType.fish_type_id)
    ).all()

    override_rows = db.execute(
        select(TripCustomerRate.fish_type_id, TripCustomerRate.trip_customer_id)
        .join(
            TripCustomer,
            TripCustomer.id == TripCustomerRate.trip_customer_id,
        )
        .where(TripCustomer.trip_id == trip_id)
        .order_by(TripCustomerRate.trip_customer_id)
    ).all()
    overrides: dict[int, list[int]] = {}
    for fish_type_id, trip_customer_id in override_rows:
        overrides.setdefault(fish_type_id, []).append(trip_customer_id)

    return [
        RateStatusRead(
            fish_type_id=trip_fish.fish_type_id,
            fish_type_name=name,
            default_set=trip_fish.rate_per_bag is not None,
            override_trip_customer_ids=overrides.get(
                trip_fish.fish_type_id, []
            ),
        )
        for trip_fish, name in fish_rows
    ]   