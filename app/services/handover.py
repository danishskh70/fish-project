from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.handover import Handover, HandoverLine
from app.models.supplier_delivery import SupplierDelivery, SupplierDeliveryItem
from app.models.trip import Trip
from app.models.trip_customer import TripCustomer
from app.models.trip_customer_rate import TripCustomerRate
from app.models.trip_fish_type import TripFishType
from app.schemas.handover import (
    CustomerTotalRead,
    HandoverCreate,
    HandoverLineRead,
    HandoverRead,
    StockLineRead,
)


def _require_trip(db: Session, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise LookupError("Trip not found.")
    return trip


def _fish_names(db: Session, fish_type_ids: set[int]) -> dict[int, str]:
    if not fish_type_ids:
        return {}
    rows = db.execute(
        select(FishType.id, FishType.name).where(FishType.id.in_(fish_type_ids))
    ).all()
    return {row[0]: row[1] for row in rows}


def _build_handover_read(
    db: Session,
    handover: Handover,
    trip_customer: TripCustomer,
) -> HandoverRead:
    lines = db.scalars(
        select(HandoverLine)
        .where(HandoverLine.handover_id == handover.id)
        .order_by(HandoverLine.id)
    ).all()
    names = _fish_names(db, {line.fish_type_id for line in lines})

    return HandoverRead(
        id=handover.id,
        trip_id=trip_customer.trip_id,
        trip_customer_id=handover.trip_customer_id,
        customer_id=trip_customer.customer_id,
        submit_reference=handover.submit_reference,
        handed_over_at=handover.handed_over_at,
        note=handover.note,
        created_at=handover.created_at,
        lines=[
            HandoverLineRead(
                fish_type_id=line.fish_type_id,
                fish_type_name=names[line.fish_type_id],
                bags=line.bags,
            )
            for line in lines
        ],
    )


def _replay(
    db: Session,
    existing: Handover,
    data: HandoverCreate,
) -> HandoverRead:
    """Same reference seen before. Same data -> return it. Else conflict."""
    existing_lines = db.scalars(
        select(HandoverLine).where(HandoverLine.handover_id == existing.id)
    ).all()
    existing_payload = {line.fish_type_id: line.bags for line in existing_lines}
    new_payload = {line.fish_type_id: line.bags for line in data.lines}

    if (
        existing.trip_customer_id != data.trip_customer_id
        or existing_payload != new_payload
    ):
        raise RuntimeError("Submit reference already used with different data.")

    trip_customer = db.get(TripCustomer, existing.trip_customer_id)
    return _build_handover_read(db, existing, trip_customer)


def _find_by_reference(db: Session, reference: str) -> Handover | None:
    return db.scalar(
        select(Handover).where(Handover.submit_reference == reference)
    )

def _resolve_rates(
    db: Session,
    trip_id: int,
    trip_customer_id: int,
    fish_type_ids: set[int],
) -> dict[int, Decimal | None]:
    """Rate to save on each line: customer override, else trip default."""
    default_rows = db.execute(
        select(TripFishType.fish_type_id, TripFishType.rate_per_bag).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id.in_(fish_type_ids),
        )
    ).all()
    rates = {row[0]: row[1] for row in default_rows}

    override_rows = db.execute(
        select(
            TripCustomerRate.fish_type_id,
            TripCustomerRate.rate_per_bag,
        ).where(
            TripCustomerRate.trip_customer_id == trip_customer_id,
            TripCustomerRate.fish_type_id.in_(fish_type_ids),
        )
    ).all()
    for fish_type_id, rate in override_rows:
        rates[fish_type_id] = rate

    return {fish_type_id: rates.get(fish_type_id) for fish_type_id in fish_type_ids}


def record_handover(
    db: Session,
    trip_id: int,
    data: HandoverCreate,
) -> tuple[HandoverRead, bool]:
    """Returns (handover, created). created=False means idempotent replay."""
    trip = db.scalar(
        select(Trip).where(Trip.id == trip_id).with_for_update()
    )
    if trip is None:
        raise LookupError("Trip not found.")
    if trip.status == "CLOSED":
        raise RuntimeError("Trip is closed.")

    trip_customer = db.scalar(
        select(TripCustomer).where(
            TripCustomer.id == data.trip_customer_id,
            TripCustomer.trip_id == trip_id,
        )
    )
    if trip_customer is None:
        raise LookupError("Trip customer not found for this trip.")

    fish_type_ids = {line.fish_type_id for line in data.lines}
    names = _fish_names(db, fish_type_ids)
    for fish_type_id in fish_type_ids:
        if fish_type_id not in names:
            raise LookupError(f"Fish type {fish_type_id} not found.")

    existing = _find_by_reference(db, data.submit_reference)
    if existing is not None:
        return _replay(db, existing, data), False

    rates = _resolve_rates(db, trip_id, trip_customer.id, fish_type_ids)


    try:
        values = {
            "trip_customer_id": trip_customer.id,
            "submit_reference": data.submit_reference,
            "note": data.note,
        }
        if data.handed_over_at is not None:
            values["handed_over_at"] = data.handed_over_at

        handover = Handover(**values)
        db.add(handover)
        db.flush()

        for line in data.lines:
            db.add(
                HandoverLine(
                    handover_id=handover.id,
                    fish_type_id=line.fish_type_id,
                    bags=line.bags,
                    rate_per_bag=rates[line.fish_type_id],
                )
            )

        db.flush()
        db.refresh(handover)
        result = _build_handover_read(db, handover, trip_customer)
        db.commit()
        return result, True
    except IntegrityError:
        db.rollback()
        # Double tap race: other request won the unique reference.
        existing = _find_by_reference(db, data.submit_reference)
        if existing is None:
            raise
        return _replay(db, existing, data), False
    except Exception:
        db.rollback()
        raise


def list_handovers(db: Session, trip_id: int) -> list[HandoverRead]:
    _require_trip(db, trip_id)
    rows = db.execute(
        select(Handover, TripCustomer)
        .join(TripCustomer, TripCustomer.id == Handover.trip_customer_id)
        .where(TripCustomer.trip_id == trip_id)
        .order_by(Handover.id)
    ).all()
    return [_build_handover_read(db, h, tc) for h, tc in rows]


def get_handover(db: Session, trip_id: int, handover_id: int) -> HandoverRead:
    row = db.execute(
        select(Handover, TripCustomer)
        .join(TripCustomer, TripCustomer.id == Handover.trip_customer_id)
        .where(Handover.id == handover_id, TripCustomer.trip_id == trip_id)
    ).first()
    if row is None:
        raise LookupError("Handover not found for this trip.")
    return _build_handover_read(db, row[0], row[1])


def get_stock(db: Session, trip_id: int) -> list[StockLineRead]:
    _require_trip(db, trip_id)

    slip_rows = db.execute(
        select(
            SupplierDeliveryItem.fish_type_id,
            func.sum(SupplierDeliveryItem.delivered_bags),
            func.sum(SupplierDeliveryItem.rejected_bags),
            func.sum(SupplierDeliveryItem.damaged_bags),
        )
        .join(
            SupplierDelivery,
            SupplierDelivery.id == SupplierDeliveryItem.delivery_id,
        )
        .where(SupplierDelivery.trip_id == trip_id)
        .group_by(SupplierDeliveryItem.fish_type_id)
    ).all()
    slip = {row[0]: (int(row[1]), int(row[2]), int(row[3])) for row in slip_rows}

    handed_rows = db.execute(
        select(HandoverLine.fish_type_id, func.sum(HandoverLine.bags))
        .join(Handover, Handover.id == HandoverLine.handover_id)
        .join(TripCustomer, TripCustomer.id == Handover.trip_customer_id)
        .where(TripCustomer.trip_id == trip_id)
        .group_by(HandoverLine.fish_type_id)
    ).all()
    handed = {row[0]: int(row[1]) for row in handed_rows}

    all_ids = set(slip) | set(handed)
    names = _fish_names(db, all_ids)

    result = []
    for fish_type_id in sorted(all_ids):
        slip_bags, rejected, damaged = slip.get(fish_type_id, (0, 0, 0))
        result.append(
            StockLineRead(
                fish_type_id=fish_type_id,
                fish_type_name=names[fish_type_id],
                on_slip=fish_type_id in slip,
                slip_bags=slip_bags,
                rejected_bags=rejected,
                damaged_bags=damaged,
                handed_bags=handed.get(fish_type_id, 0),
            )
        )
    return result


def get_customer_totals(db: Session, trip_id: int) -> list[CustomerTotalRead]:
    _require_trip(db, trip_id)
    rows = db.execute(
        select(
            TripCustomer.id,
            TripCustomer.customer_id,
            HandoverLine.fish_type_id,
            func.sum(HandoverLine.bags),
        )
        .join(Handover, Handover.trip_customer_id == TripCustomer.id)
        .join(HandoverLine, HandoverLine.handover_id == Handover.id)
        .where(TripCustomer.trip_id == trip_id)
        .group_by(
            TripCustomer.id, TripCustomer.customer_id, HandoverLine.fish_type_id
        )
        .order_by(TripCustomer.id, HandoverLine.fish_type_id)
    ).all()
    names = _fish_names(db, {row[2] for row in rows})
    return [
        CustomerTotalRead(
            trip_customer_id=row[0],
            customer_id=row[1],
            fish_type_id=row[2],
            fish_type_name=names[row[2]],
            bags=int(row[3]),
        )
        for row in rows
    ]