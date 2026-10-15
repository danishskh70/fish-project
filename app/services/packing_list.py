from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.packing_list import PackingList
from app.models.packing_list_item import PackingListItem
from app.models.trip import Trip
from app.models.trip_fish_type import TripFishType
from app.schemas.packing_list import (
    PackingListCreate,
    PackingListItemAdd,
    PackingListItemRead,
    PackingListRead,
)


def create_packing_list(
    db: Session,
    trip_id: int,
    data: PackingListCreate,
) -> PackingListRead:
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise ValueError("Trip not found.")

    existing_list = db.scalar(
        select(PackingList).where(
            PackingList.trip_id == trip_id,
        )
    )

    if existing_list is not None:
        raise ValueError("A packing list already exists for this trip.")

    fish_type_ids = [item.fish_type_id for item in data.items]

    if len(fish_type_ids) != len(set(fish_type_ids)):
        raise ValueError("Duplicate fish types are not allowed.")

    fish_types = list(
        db.scalars(
            select(FishType).where(
                FishType.id.in_(fish_type_ids),
            )
        ).all()
    )
    fish_types_by_id = {
        fish_type.id: fish_type
        for fish_type in fish_types
    }

    for fish_type_id in fish_type_ids:
        fish_type = fish_types_by_id.get(fish_type_id)

        if fish_type is None:
            raise ValueError(
                f"Fish type {fish_type_id} not found."
            )

        if not fish_type.is_active:
            raise ValueError(
                f"Cannot pack inactive fish type {fish_type_id}."
            )

    existing_associations = db.scalars(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
        )
    ).all()
    trip_fish_type_ids = {
        association.fish_type_id
        for association in existing_associations
    }

    try:
        packing_list = PackingList(trip_id=trip_id)
        db.add(packing_list)
        db.flush()

        for item_data in data.items:
            if item_data.fish_type_id not in trip_fish_type_ids:
                db.add(
                    TripFishType(
                        trip_id=trip_id,
                        fish_type_id=item_data.fish_type_id,
                        planned_quantity_bags=None,
                    )
                )
                trip_fish_type_ids.add(item_data.fish_type_id)

            db.add(
                PackingListItem(
                    packing_list_id=packing_list.id,
                    fish_type_id=item_data.fish_type_id,
                    quantity_bags=item_data.quantity_bags,
                )
            )

        db.flush()

        saved_items = db.scalars(
            select(PackingListItem)
            .where(
                PackingListItem.packing_list_id == packing_list.id,
            )
            .order_by(PackingListItem.id)
        ).all()

        response = PackingListRead(
            id=packing_list.id,
            trip_id=packing_list.trip_id,
            created_at=packing_list.created_at,
            items=[
                PackingListItemRead.model_validate(item)
                for item in saved_items
            ],
            total_bags=sum(
                item.quantity_bags for item in saved_items
            ),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise


def update_packing_list_item_quantity(
    db: Session,
    trip_id: int,
    fish_type_id: int,
    quantity_bags: int,
) -> PackingListRead:
    packing_list = db.scalar(
        select(PackingList).where(
            PackingList.trip_id == trip_id,
        )
    )

    if packing_list is None:
        raise ValueError("Packing list not found for this trip.")

    item = db.scalar(
        select(PackingListItem).where(
            PackingListItem.packing_list_id == packing_list.id,
            PackingListItem.fish_type_id == fish_type_id,
        )
    )

    if item is None:
        raise ValueError("Fish type not found in this packing list.")

    try:
        item.quantity_bags = quantity_bags
        db.flush()

        saved_items = db.scalars(
            select(PackingListItem)
            .where(
                PackingListItem.packing_list_id == packing_list.id,
            )
            .order_by(PackingListItem.id)
        ).all()

        response = PackingListRead(
            id=packing_list.id,
            trip_id=packing_list.trip_id,
            created_at=packing_list.created_at,
            items=[
                PackingListItemRead.model_validate(saved_item)
                for saved_item in saved_items
            ],
            total_bags=sum(
                saved_item.quantity_bags
                for saved_item in saved_items
            ),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise


def add_packing_list_item(
    db: Session,
    trip_id: int,
    data: PackingListItemAdd,
) -> PackingListRead:
    packing_list = db.scalar(
        select(PackingList).where(
            PackingList.trip_id == trip_id,
        )
    )

    if packing_list is None:
        raise ValueError("Packing list not found for this trip.")

    fish_type = db.get(FishType, data.fish_type_id)

    if fish_type is None:
        raise ValueError(
            f"Fish type {data.fish_type_id} not found."
        )

    if not fish_type.is_active:
        raise ValueError(
            f"Cannot add inactive fish type {data.fish_type_id}."
        )

    existing_item = db.scalar(
        select(PackingListItem).where(
            PackingListItem.packing_list_id == packing_list.id,
            PackingListItem.fish_type_id == data.fish_type_id,
        )
    )

    if existing_item is not None:
        raise ValueError(
            "Fish type already exists in this packing list. "
            "Use the quantity update endpoint instead."
        )

    try:
        trip_fish_type = db.scalar(
            select(TripFishType).where(
                TripFishType.trip_id == trip_id,
                TripFishType.fish_type_id == data.fish_type_id,
            )
        )

        if trip_fish_type is None:
            db.add(
                TripFishType(
                    trip_id=trip_id,
                    fish_type_id=data.fish_type_id,
                    planned_quantity_bags=None,
                )
            )

        db.add(
            PackingListItem(
                packing_list_id=packing_list.id,
                fish_type_id=data.fish_type_id,
                quantity_bags=data.quantity_bags,
            )
        )
        db.flush()

        saved_items = db.scalars(
            select(PackingListItem)
            .where(
                PackingListItem.packing_list_id == packing_list.id,
            )
            .order_by(PackingListItem.id)
        ).all()

        response = PackingListRead(
            id=packing_list.id,
            trip_id=packing_list.trip_id,
            created_at=packing_list.created_at,
            items=[
                PackingListItemRead.model_validate(item)
                for item in saved_items
            ],
            total_bags=sum(
                item.quantity_bags for item in saved_items
            ),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise

def get_packing_list(
    db: Session,
    trip_id: int,
) -> PackingListRead:
    packing_list = db.scalar(
        select(PackingList).where(
            PackingList.trip_id == trip_id,
        )
    )

    if packing_list is None:
        raise ValueError("Packing list not found for this trip.")

    saved_items = db.scalars(
        select(PackingListItem)
        .where(
            PackingListItem.packing_list_id == packing_list.id,
        )
        .order_by(PackingListItem.id)
    ).all()

    return PackingListRead(
        id=packing_list.id,
        trip_id=packing_list.trip_id,
        created_at=packing_list.created_at,
        items=[
            PackingListItemRead.model_validate(item)
            for item in saved_items
        ],
        total_bags=sum(
            item.quantity_bags for item in saved_items
        ),
    )


def remove_packing_list_item(
    db: Session,
    trip_id: int,
    fish_type_id: int,
) -> PackingListRead:
    packing_list = db.scalar(
        select(PackingList).where(
            PackingList.trip_id == trip_id,
        )
    )

    if packing_list is None:
        raise ValueError("Packing list not found for this trip.")

    items = db.scalars(
        select(PackingListItem)
        .where(
            PackingListItem.packing_list_id == packing_list.id,
        )
        .order_by(PackingListItem.id)
    ).all()

    item_to_remove = next(
        (
            item for item in items
            if item.fish_type_id == fish_type_id
        ),
        None,
    )

    if item_to_remove is None:
        raise ValueError(
            "Fish type not found in this packing list."
        )

    if len(items) == 1:
        raise ValueError(
            "Cannot remove the last fish type from a packing list."
        )

    try:
        db.delete(item_to_remove)
        db.flush()

        remaining_items = [
            item for item in items
            if item.fish_type_id != fish_type_id
        ]

        response = PackingListRead(
            id=packing_list.id,
            trip_id=packing_list.trip_id,
            created_at=packing_list.created_at,
            items=[
                PackingListItemRead.model_validate(item)
                for item in remaining_items
            ],
            total_bags=sum(
                item.quantity_bags
                for item in remaining_items
            ),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise
