
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.bill import BillRead
from app.schemas.handover import (
    CustomerTotalRead,
    HandoverCreate,
    HandoverRead,
    StockLineRead,
)
from app.schemas.packing_list import (
    PackingListCreate,
    PackingListItemAdd,
    PackingListItemQuantityUpdate,
    PackingListRead,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentRead,
    PaymentSummaryRead,
    PaymentVoid,
)
from app.schemas.rate import RateSetRead, RatesSet, RateStatusRead
from app.schemas.supplier_delivery import SupplierDeliveryCreate, SupplierDeliveryRead
from app.schemas.supplier_list import SupplierListRead
from app.schemas.supplier_list_item_update import SupplierListItemUpdate
from app.schemas.trip import (
    TripCreate,
    TripFishTypeAdd,
    TripPlannedQuantityUpdate,
    TripRead,
)
from app.schemas.trip_close import TripCloseRead
from app.schemas.trip_requirements_table import TripRequirementsTableRead
from app.services.bill import get_bill
from app.services.handover import (
    get_customer_totals,
    get_handover,
    get_stock,
    list_handovers,
    record_handover,
)
from app.services.packing_list import (
    add_packing_list_item,
    create_packing_list,
    get_packing_list,
    remove_packing_list_item,
    update_packing_list_item_quantity,
)
from app.services.payment import (
    get_payment_summary,
    list_payments,
    record_payment,
    void_payment,
)
from app.services.rate import (
    get_rate_status,
    set_customer_rates,
    set_trip_rates,
)
from app.services.supplier_delivery import (
    get_supplier_delivery,
    list_supplier_deliveries,
    record_supplier_delivery,
)
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
    close_trip,
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

@router.post(
    "/{trip_id}/packing-list",
    response_model=PackingListRead,
    status_code=status.HTTP_201_CREATED,
)
def create_packing_list_endpoint(
    trip_id: int,
    data: PackingListCreate,
    db: Session = Depends(get_db),
) -> PackingListRead:
    try:
        return create_packing_list(db, trip_id, data)
    except ValueError as exc:
        message = str(exc)

        if message == "Trip not found.":
            status_code = status.HTTP_404_NOT_FOUND
        elif message == "A packing list already exists for this trip.":
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc

@router.patch(
    "/{trip_id}/packing-list/items/{fish_type_id}",
    response_model=PackingListRead,
)
def update_packing_list_item_quantity_endpoint(
    trip_id: int,
    fish_type_id: int,
    data: PackingListItemQuantityUpdate,
    db: Session = Depends(get_db),
) -> PackingListRead:
    try:
        return update_packing_list_item_quantity(
            db=db,
            trip_id=trip_id,
            fish_type_id=fish_type_id,
            quantity_bags=data.quantity_bags,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Packing list not found for this trip." or message == "Fish type not found in this packing list.":
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc

@router.post(
    "/{trip_id}/packing-list/items",
    response_model=PackingListRead,
    status_code=status.HTTP_201_CREATED,
)
def add_packing_list_item_endpoint(
    trip_id: int,
    data: PackingListItemAdd,
    db: Session = Depends(get_db),
) -> PackingListRead:
    try:
        return add_packing_list_item(
            db=db,
            trip_id=trip_id,
            data=data,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Packing list not found for this trip." or "not found" in message.lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "already exists" in message.lower():
            status_code = status.HTTP_409_CONFLICT
        elif "inactive" in message.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc


@router.get(
    "/{trip_id}/packing-list",
    response_model=PackingListRead,
)
def get_packing_list_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> PackingListRead:
    try:
        return get_packing_list(
            db=db,
            trip_id=trip_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{trip_id}/packing-list/items/{fish_type_id}",
    response_model=PackingListRead,
)
def remove_packing_list_item_endpoint(
    trip_id: int,
    fish_type_id: int,
    db: Session = Depends(get_db),
) -> PackingListRead:
    try:
        return remove_packing_list_item(
            db=db,
            trip_id=trip_id,
            fish_type_id=fish_type_id,
        )
    except ValueError as exc:
        message = str(exc)

        if "not found" in message.lower():
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc


@router.post(
    "/{trip_id}/supplier-deliveries",
    response_model=SupplierDeliveryRead,
    status_code=status.HTTP_201_CREATED,
)
def record_supplier_delivery_endpoint(
    trip_id: int,
    data: SupplierDeliveryCreate,
    db: Session = Depends(get_db),
) -> SupplierDeliveryRead:
    try:
        return record_supplier_delivery(db, trip_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{trip_id}/supplier-deliveries",
    response_model=list[SupplierDeliveryRead],
)
def list_supplier_deliveries_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[SupplierDeliveryRead]:
    try:
        return list_supplier_deliveries(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{trip_id}/supplier-deliveries/{delivery_id}",
    response_model=SupplierDeliveryRead,
)
def get_supplier_delivery_endpoint(
    trip_id: int,
    delivery_id: int,
    db: Session = Depends(get_db),
) -> SupplierDeliveryRead:
    try:
        return get_supplier_delivery(db, trip_id, delivery_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post(
    "/{trip_id}/handovers",
    response_model=HandoverRead,
    status_code=status.HTTP_201_CREATED,
)
def record_handover_endpoint(
    trip_id: int,
    data: HandoverCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> HandoverRead:
    try:
        result, created = record_handover(db, trip_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/{trip_id}/handovers", response_model=list[HandoverRead])
def list_handovers_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[HandoverRead]:
    try:
        return list_handovers(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/handovers/{handover_id}", response_model=HandoverRead)
def get_handover_endpoint(
    trip_id: int,
    handover_id: int,
    db: Session = Depends(get_db),
) -> HandoverRead:
    try:
        return get_handover(db, trip_id, handover_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/stock", response_model=list[StockLineRead])
def get_stock_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[StockLineRead]:
    try:
        return get_stock(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{trip_id}/handover-totals",
    response_model=list[CustomerTotalRead],
)
def get_customer_totals_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[CustomerTotalRead]:
    try:
        return get_customer_totals(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/{trip_id}/close", response_model=TripCloseRead)
def close_trip_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> TripCloseRead:
    try:
        return close_trip(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
@router.put("/{trip_id}/rates", response_model=list[RateSetRead])
def set_trip_rates_endpoint(
    trip_id: int,
    data: RatesSet,
    db: Session = Depends(get_db),
) -> list[RateSetRead]:
    try:
        return set_trip_rates(db, trip_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/{trip_id}/customers/{trip_customer_id}/rates",
    response_model=list[RateSetRead],
)
def set_customer_rates_endpoint(
    trip_id: int,
    trip_customer_id: int,
    data: RatesSet,
    db: Session = Depends(get_db),
) -> list[RateSetRead]:
    try:
        return set_customer_rates(db, trip_id, trip_customer_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/rate-status", response_model=list[RateStatusRead])
def get_rate_status_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[RateStatusRead]:
    try:
        return get_rate_status(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
        
@router.get("/{trip_id}/bill", response_model=BillRead)
def get_bill_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> BillRead:
    try:
        return get_bill(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{trip_id}/customers/{trip_customer_id}/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def record_payment_endpoint(
    trip_id: int,
    trip_customer_id: int,
    data: PaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> PaymentRead:
    try:
        result, created = record_payment(db, trip_id, trip_customer_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return result


@router.get(
    "/{trip_id}/customers/{trip_customer_id}/payments",
    response_model=list[PaymentRead],
)
def list_payments_endpoint(
    trip_id: int,
    trip_customer_id: int,
    db: Session = Depends(get_db),
) -> list[PaymentRead]:
    try:
        return list_payments(db, trip_id, trip_customer_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trip_id}/payments-summary", response_model=PaymentSummaryRead)
def get_payment_summary_endpoint(
    trip_id: int,
    db: Session = Depends(get_db),
) -> PaymentSummaryRead:
    try:
        return get_payment_summary(db, trip_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{trip_id}/customers/{trip_customer_id}/payments/{payment_id}/void",
    response_model=PaymentRead,
)
def void_payment_endpoint(
    trip_id: int,
    trip_customer_id: int,
    payment_id: int,
    data: PaymentVoid,
    db: Session = Depends(get_db),
) -> PaymentRead:
    try:
        return void_payment(db, trip_id, trip_customer_id, payment_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
