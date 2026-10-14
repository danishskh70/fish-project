
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.supplier_list import SupplierList
from app.models.supplier_list_item import SupplierListItem
from app.schemas.supplier_list import (
    SupplierListItemRead,
    SupplierListRead,
)
from app.schemas.supplier_list_item_update import SupplierListItemUpdate
from app.services.supplier_list_errors import (
    SupplierListAlreadyFinalError,
    SupplierListItemNotFoundError,
    SupplierListNotEditableError,
    SupplierListNotFoundError,
)
from app.services.trip_requirements_table import get_trip_requirements_table


def generate_supplier_list_draft(
    db: Session,
    trip_id: int,
) -> SupplierListRead:
    requirements = get_trip_requirements_table(db, trip_id)

    next_version = (
        db.scalar(
            select(func.max(SupplierList.version_number)).where(
                SupplierList.trip_id == trip_id,
            )
        )
        or 0
    ) + 1

    supplier_list = SupplierList(
        trip_id=trip_id,
        version_number=next_version,
        status="DRAFT",
    )

    try:
        db.add(supplier_list)
        db.flush()

        fish_types_by_id = {
            fish_type.id: fish_type
            for fish_type in requirements.fish_types
        }

        for fish_total in requirements.fish_totals:
            fish_type = fish_types_by_id[fish_total.fish_type_id]
            bags = fish_total.effective_planned_quantity_bags

            db.add(
                SupplierListItem(
                    supplier_list_id=supplier_list.id,
                    fish_type_id=fish_total.fish_type_id,
                    fish_type_name=fish_type.name,
                    quantity_bags=bags,
                    tub_count=(bags + 3) // 4,
                )
            )

        db.flush()

        items = db.scalars(
            select(SupplierListItem)
            .where(SupplierListItem.supplier_list_id == supplier_list.id)
            .order_by(SupplierListItem.id)
        ).all()

        response = SupplierListRead(
            id=supplier_list.id,
            trip_id=supplier_list.trip_id,
            version_number=supplier_list.version_number,
            status=supplier_list.status,
            created_at=supplier_list.created_at,
            finalized_at=supplier_list.finalized_at,
            items=[SupplierListItemRead.model_validate(item) for item in items],
            total_bags=sum(item.quantity_bags for item in items),
            total_tubs=sum(item.tub_count for item in items),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise



def update_supplier_list_item(
    db: Session,
    trip_id: int,
    supplier_list_id: int,
    fish_type_id: int,
    update: SupplierListItemUpdate,
) -> SupplierListRead:
    supplier_list = db.scalar(
        select(SupplierList).where(
            SupplierList.id == supplier_list_id,
            SupplierList.trip_id == trip_id,
        )
    )
    if supplier_list is None:
        raise SupplierListNotFoundError(
            "Supplier list not found for this trip."
        )

    if supplier_list.status != "DRAFT":
        raise SupplierListNotEditableError(
            "Only draft supplier lists can be edited."
        )

    item = db.scalar(
        select(SupplierListItem).where(
            SupplierListItem.supplier_list_id == supplier_list_id,
            SupplierListItem.fish_type_id == fish_type_id,
        )
    )
    if item is None:
        raise SupplierListItemNotFoundError(
            "Fish type not found in this supplier list."
        )

    try:
        if "quantity_bags" in update.model_fields_set:
            item.quantity_bags = update.quantity_bags
            item.tub_count = (item.quantity_bags + 3) // 4
        elif "tub_count" in update.model_fields_set:
            item.tub_count = update.tub_count

        db.flush()

        items = db.scalars(
            select(SupplierListItem)
            .where(
                SupplierListItem.supplier_list_id == supplier_list.id,
            )
            .order_by(SupplierListItem.id)
        ).all()

        response = SupplierListRead(
            id=supplier_list.id,
            trip_id=supplier_list.trip_id,
            version_number=supplier_list.version_number,
            status=supplier_list.status,
            created_at=supplier_list.created_at,
            finalized_at=supplier_list.finalized_at,
            items=[
                SupplierListItemRead.model_validate(saved_item)
                for saved_item in items
            ],
            total_bags=sum(saved_item.quantity_bags for saved_item in items),
            total_tubs=sum(saved_item.tub_count for saved_item in items),
        )

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise

def finalize_supplier_list(
    db: Session,
    trip_id: int,
    supplier_list_id: int,
) -> SupplierListRead:
    supplier_list = db.scalar(
        select(SupplierList).where(
            SupplierList.id == supplier_list_id,
            SupplierList.trip_id == trip_id,
        )
    )

    if supplier_list is None:
        raise SupplierListNotFoundError(
            "Supplier list not found for this trip."
        )

    if supplier_list.status != "DRAFT":
        raise SupplierListNotEditableError(
            "Only draft supplier lists can be finalized."
        )

    existing_final = db.scalar(
        select(SupplierList).where(
            SupplierList.trip_id == trip_id,
            SupplierList.status == "FINAL",
        )
    )

    if existing_final is not None:
        raise SupplierListAlreadyFinalError(
            "This trip already has a final supplier list."
        )

    try:
        supplier_list.status = "FINAL"
        supplier_list.finalized_at = datetime.now(UTC)

        db.commit()
        db.refresh(supplier_list)

        items = db.scalars(
            select(SupplierListItem)
            .where(SupplierListItem.supplier_list_id == supplier_list.id)
            .order_by(SupplierListItem.id)
        ).all()

        return SupplierListRead(
            id=supplier_list.id,
            trip_id=supplier_list.trip_id,
            version_number=supplier_list.version_number,
            status=supplier_list.status,
            created_at=supplier_list.created_at,
            finalized_at=supplier_list.finalized_at,
            items=[
                SupplierListItemRead.model_validate(item)
                for item in items
            ],
            total_bags=sum(item.quantity_bags for item in items),
            total_tubs=sum(item.tub_count for item in items),
        )

    except Exception:
        db.rollback()
        raise

def _build_supplier_list_read(
    db: Session,
    supplier_list: SupplierList,
) -> SupplierListRead:
    items = db.scalars(
        select(SupplierListItem)
        .where(SupplierListItem.supplier_list_id == supplier_list.id)
        .order_by(SupplierListItem.id)
    ).all()

    return SupplierListRead(
        id=supplier_list.id,
        trip_id=supplier_list.trip_id,
        version_number=supplier_list.version_number,
        status=supplier_list.status,
        created_at=supplier_list.created_at,
        finalized_at=supplier_list.finalized_at,
        items=[SupplierListItemRead.model_validate(item) for item in items],
        total_bags=sum(item.quantity_bags for item in items),
        total_tubs=sum(item.tub_count for item in items),
    )


def list_supplier_lists(
    db: Session,
    trip_id: int,
) -> list[SupplierListRead]:
    from app.models.trip import Trip

    trip = db.get(Trip, trip_id)
    if trip is None:
        raise SupplierListNotFoundError("Trip not found.")

    supplier_lists = db.scalars(
        select(SupplierList)
        .where(SupplierList.trip_id == trip_id)
        .order_by(SupplierList.version_number.desc())
    ).all()

    return [
        _build_supplier_list_read(db, supplier_list)
        for supplier_list in supplier_lists
    ]


def get_supplier_list(
    db: Session,
    trip_id: int,
    supplier_list_id: int,
) -> SupplierListRead:
    supplier_list = db.scalar(
        select(SupplierList).where(
            SupplierList.id == supplier_list_id,
            SupplierList.trip_id == trip_id,
        )
    )

    if supplier_list is None:
        raise SupplierListNotFoundError(
            "Supplier list not found for this trip."
        )

    return _build_supplier_list_read(db, supplier_list)
