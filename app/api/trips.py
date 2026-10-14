
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.supplier_list import SupplierListRead
from app.schemas.supplier_list_item_update import SupplierListItemUpdate
from app.schemas.trip import (
    TripCreate,
    TripFishTypeAdd,
    TripPlannedQuantityUpdate,
    TripRead,
)
from app.schemas.trip_requirements_table import TripRequirementsTableRead
from app.services.supplier_list import (
    finalize_supplier_list,
    generate_supplier_list_draft,
    get_supplier_list,
    list_supplier_lists,
    update_supplier_list_item,
)
from app.services.supplier_list_errors import (
    SupplierListAlreadyFinalError,
    SupplierListItemNotFoundError,
    SupplierListNotEditableError,
    SupplierListNotFoundError,
)
from app.services.trip import (
    add_fish_type_to_trip,
    create_trip,
    get_trip,
    list_trips,
    update_trip_fish_type_planned_quantity,
)
from app.services.trip_requirements_table import (
    TripRequirementsTableNotFoundError,
    get_trip_requirements_table,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("/", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip_endpoint(
    trip_data: TripCreate,
    db: Session = Depends(get_db),
) -> TripRead:
    try:
        return create_trip(db, trip_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=list[TripRead])
def list_trips_endpoint(
    db: Session = Depends(get_db),
) -> list[TripRead]:
    return list_trips(db)


@router.get("/{trip_id}", response_model=TripRead)
def get_trip_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> TripRead:
    trip = get_trip(db, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )

    return trip
@router.post(
    "/{trip_id}/fish-types",
    status_code=status.HTTP_201_CREATED,
)
def add_fish_type_to_trip_endpoint(
    trip_id: int,
    data: TripFishTypeAdd,
    db: Session = Depends(get_db),
):
    try:
        return add_fish_type_to_trip(
            db,
            trip_id,
            data.fish_type_id,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Trip not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        if message == "Fish type is already configured for this trip.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc


@router.get(
    "/{trip_id}/requirements-table",
    response_model=TripRequirementsTableRead,
)
def get_trip_requirements_table_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> TripRequirementsTableRead:
    try:
        return get_trip_requirements_table(db, trip_id)
    except TripRequirementsTableNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        ) from exc

@router.patch(
    "/{trip_id}/fish-types/{fish_type_id}/planned-quantity",
)
def update_trip_fish_type_planned_quantity_endpoint(
    trip_id: int,
    fish_type_id: int,
    data: TripPlannedQuantityUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_trip_fish_type_planned_quantity(
            db,
            trip_id,
            fish_type_id,
            data.planned_quantity_bags,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{trip_id}/supplier-lists/drafts",
    response_model=SupplierListRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_supplier_list_draft_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> SupplierListRead:
    try:
        return generate_supplier_list_draft(db, trip_id)
    except TripRequirementsTableNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        ) from exc

@router.patch(
    "/{trip_id}/supplier-lists/{supplier_list_id}/items/{fish_type_id}",
    response_model=SupplierListRead,
)
def update_supplier_list_item_endpoint(
    trip_id: int,
    supplier_list_id: int,
    fish_type_id: int,
    update: SupplierListItemUpdate,
    db: Session = Depends(get_db),
) -> SupplierListRead:
    try:
        return update_supplier_list_item(
            db=db,
            trip_id=trip_id,
            supplier_list_id=supplier_list_id,
            fish_type_id=fish_type_id,
            update=update,
        )
    except SupplierListNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupplierListItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupplierListNotEditableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

@router.post(
    "/{trip_id}/supplier-lists/{supplier_list_id}/finalize",
    response_model=SupplierListRead,
)
def finalize_supplier_list_endpoint(
    trip_id: int,
    supplier_list_id: int,
    db: Session = Depends(get_db),
) -> SupplierListRead:
    try:
        return finalize_supplier_list(
            db=db,
            trip_id=trip_id,
            supplier_list_id=supplier_list_id,
        )
    except SupplierListNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupplierListNotEditableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SupplierListAlreadyFinalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
@router.get(
    "/{trip_id}/supplier-lists",
    response_model=list[SupplierListRead],
)
def read_supplier_lists(
    trip_id: int,
    db: Session = Depends(get_db),
):
    try:
        return list_supplier_lists(db, trip_id)
    except SupplierListNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{trip_id}/supplier-lists/{supplier_list_id}",
    response_model=SupplierListRead,
)
def read_supplier_list(
    trip_id: int,
    supplier_list_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_supplier_list(db, trip_id, supplier_list_id)
    except SupplierListNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc