from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.supplier_delivery import SupplierDelivery, SupplierDeliveryItem
from app.models.supplier_list import SupplierList
from app.models.supplier_list_item import SupplierListItem
from app.models.trip import Trip
from app.schemas.supplier_delivery import (
    SupplierDeliveryCreate,
    SupplierDeliveryItemRead,
    SupplierDeliveryRead,
)


def _build_supplier_delivery_read(
    db: Session,
    delivery: SupplierDelivery,
) -> SupplierDeliveryRead:
    items = db.scalars(
        select(SupplierDeliveryItem)
        .where(SupplierDeliveryItem.delivery_id == delivery.id)
        .order_by(SupplierDeliveryItem.id)
    ).all()

    return SupplierDeliveryRead(
        id=delivery.id,
        trip_id=delivery.trip_id,
        supplier_list_id=delivery.supplier_list_id,
        tub_count=delivery.tub_count,
        vehicle=delivery.vehicle,
        driver=delivery.driver,
        received_at=delivery.received_at,
        items=[SupplierDeliveryItemRead.model_validate(item) for item in items],
    )


def record_supplier_delivery(
    db: Session,
    trip_id: int,
    data: SupplierDeliveryCreate,
) -> SupplierDeliveryRead:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise LookupError("Trip not found.")

    planned_by_fish_type_id: dict[int, SupplierListItem] = {}

    if data.supplier_list_id is not None:
        supplier_list = db.get(SupplierList, data.supplier_list_id)
        if supplier_list is None:
            raise LookupError("Supplier list not found.")

        if supplier_list.trip_id != trip_id:
            raise ValueError(
                "Supplier list does not belong to this trip."
            )

        if supplier_list.status != "FINAL":
            raise RuntimeError(
                "Only finalized supplier lists can receive deliveries."
            )

        existing = db.scalar(
            select(SupplierDelivery).where(
                SupplierDelivery.supplier_list_id == supplier_list.id
            )
        )
        if existing is not None:
            raise RuntimeError("Delivery has already been recorded.")

        planned_items = db.scalars(
            select(SupplierListItem).where(
                SupplierListItem.supplier_list_id == supplier_list.id
            )
        ).all()
        planned_by_fish_type_id = {
            item.fish_type_id: item for item in planned_items
        }

    fish_type_ids = [item.fish_type_id for item in data.items]
    fish_types = db.scalars(
        select(FishType).where(FishType.id.in_(fish_type_ids))
    ).all()
    fish_types_by_id = {fish_type.id: fish_type for fish_type in fish_types}

    for fish_type_id in fish_type_ids:
        if fish_type_id not in fish_types_by_id:
            raise LookupError(f"Fish type {fish_type_id} not found.")

    try:
        delivery = SupplierDelivery(
            trip_id=trip_id,
            supplier_list_id=data.supplier_list_id,
            tub_count=data.tub_count,
            vehicle=data.vehicle,
            driver=data.driver,
        )
        db.add(delivery)
        db.flush()

        items = []
        for submitted in data.items:
            fish_type = fish_types_by_id[submitted.fish_type_id]
            planned = planned_by_fish_type_id.get(submitted.fish_type_id)

            item = SupplierDeliveryItem(
                delivery_id=delivery.id,
                fish_type_id=submitted.fish_type_id,
                fish_type_name=fish_type.name,
                planned_bags=(
                    planned.quantity_bags if planned is not None else None
                ),
                delivered_bags=submitted.delivered_bags,
                rejected_bags=submitted.rejected_bags,
                damaged_bags=submitted.damaged_bags,
            )
            db.add(item)
            items.append(item)

        db.flush()
        db.refresh(delivery)

        result = SupplierDeliveryRead(
            id=delivery.id,
            trip_id=delivery.trip_id,
            supplier_list_id=delivery.supplier_list_id,
            tub_count=delivery.tub_count,
            vehicle=delivery.vehicle,
            driver=delivery.driver,
            received_at=delivery.received_at,
            items=[
                SupplierDeliveryItemRead.model_validate(item)
                for item in items
            ],
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def list_supplier_deliveries(
    db: Session,
    trip_id: int,
) -> list[SupplierDeliveryRead]:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise LookupError("Trip not found.")

    deliveries = db.scalars(
        select(SupplierDelivery)
        .where(SupplierDelivery.trip_id == trip_id)
        .order_by(SupplierDelivery.id)
    ).all()

    return [
        _build_supplier_delivery_read(db, delivery)
        for delivery in deliveries
    ]


def get_supplier_delivery(
    db: Session,
    trip_id: int,
    delivery_id: int,
) -> SupplierDeliveryRead:
    delivery = db.scalar(
        select(SupplierDelivery).where(
            SupplierDelivery.id == delivery_id,
            SupplierDelivery.trip_id == trip_id,
        )
    )
    if delivery is None:
        raise LookupError("Supplier delivery not found for this trip.")

    return _build_supplier_delivery_read(db, delivery)
