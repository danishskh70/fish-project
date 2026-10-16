from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier_delivery import SupplierDelivery, SupplierDeliveryItem
from app.models.supplier_list import SupplierList
from app.models.supplier_list_item import SupplierListItem
from app.schemas.supplier_delivery import (
    SupplierDeliveryCreate,
    SupplierDeliveryItemRead,
    SupplierDeliveryRead,
)


def record_supplier_delivery(
    db: Session,
    trip_id: int,
    supplier_list_id: int,
    data: SupplierDeliveryCreate,
) -> SupplierDeliveryRead:
    supplier_list = db.scalar(
        select(SupplierList).where(
            SupplierList.id == supplier_list_id,
            SupplierList.trip_id == trip_id,
        )
    )
    if supplier_list is None:
        raise LookupError("Supplier list not found for this trip.")

    if supplier_list.status != "FINAL":
        raise RuntimeError("Only finalized supplier lists can receive deliveries.")

    existing = db.scalar(
        select(SupplierDelivery).where(
            SupplierDelivery.supplier_list_id == supplier_list_id
        )
    )
    if existing is not None:
        raise RuntimeError("Delivery has already been recorded.")

    planned_items = db.scalars(
        select(SupplierListItem)
        .where(SupplierListItem.supplier_list_id == supplier_list_id)
        .order_by(SupplierListItem.id)
    ).all()

    planned_by_id = {item.fish_type_id: item for item in planned_items}
    submitted_by_id = {item.fish_type_id: item for item in data.items}

    if set(planned_by_id) != set(submitted_by_id):
        raise ValueError(
            "Submit exactly one delivery entry for every fish type on the finalized supplier list."
        )

    try:
        delivery = SupplierDelivery(supplier_list_id=supplier_list_id)
        db.add(delivery)
        db.flush()

        items = []
        for fish_type_id, planned in planned_by_id.items():
            received = submitted_by_id[fish_type_id]
            item = SupplierDeliveryItem(
                delivery_id=delivery.id,
                fish_type_id=fish_type_id,
                fish_type_name=planned.fish_type_name,
                planned_bags=planned.quantity_bags,
                delivered_bags=received.delivered_bags,
                rejected_bags=received.rejected_bags,
                damaged_bags=received.damaged_bags,
            )
            db.add(item)
            items.append(item)

        db.flush()
        db.refresh(delivery)

        result = SupplierDeliveryRead(
            id=delivery.id,
            supplier_list_id=delivery.supplier_list_id,
            received_at=delivery.received_at,
            items=[SupplierDeliveryItemRead.model_validate(item) for item in items],
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def get_supplier_delivery(
    db: Session,
    trip_id: int,
    supplier_list_id: int,
) -> SupplierDeliveryRead:
    supplier_list = db.scalar(
        select(SupplierList).where(
            SupplierList.id == supplier_list_id,
            SupplierList.trip_id == trip_id,
        )
    )
    if supplier_list is None:
        raise LookupError("Supplier list not found for this trip.")

    delivery = db.scalar(
        select(SupplierDelivery).where(
            SupplierDelivery.supplier_list_id == supplier_list_id
        )
    )
    if delivery is None:
        raise LookupError("No delivery has been recorded for this supplier list.")

    items = db.scalars(
        select(SupplierDeliveryItem)
        .where(SupplierDeliveryItem.delivery_id == delivery.id)
        .order_by(SupplierDeliveryItem.id)
    ).all()

    return SupplierDeliveryRead(
        id=delivery.id,
        supplier_list_id=delivery.supplier_list_id,
        received_at=delivery.received_at,
        items=[SupplierDeliveryItemRead.model_validate(item) for item in items],
    )
