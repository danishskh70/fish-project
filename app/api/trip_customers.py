from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.trip_customer import (
    TripCustomerCreate,
    TripCustomerRead,
)
from app.services.trip_customer import (
    CustomerNotFoundError,
    DuplicateTripCustomerError,
    InactiveCustomerError,
    SameTripCopyError,
    TripNotFoundError,
    add_customer_to_trip,
    copy_customers_from_trip,
    list_trip_customers,
)

router = APIRouter(prefix="/trips", tags=["Trip Customers"])


@router.post(
    "/{trip_id}/customers",
    response_model=TripCustomerRead,
    status_code=status.HTTP_201_CREATED,
)
def post_trip_customer(
    trip_id: int,
    data: TripCustomerCreate,
    db: Session = Depends(get_db),
) -> TripCustomerRead:
    try:
        return add_customer_to_trip(db, trip_id, data)
    except TripNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    except InactiveCustomerError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign an inactive customer to a trip.",
        )
    except DuplicateTripCustomerError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer is already assigned to this trip.",
        )


@router.get(
    "/{trip_id}/customers",
    response_model=list[TripCustomerRead],
)
def get_trip_customers(
    trip_id: int,
    db: Session = Depends(get_db),
) -> list[TripCustomerRead]:
    try:
        return list_trip_customers(db, trip_id)
    except TripNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )


@router.post(
    "/{destination_trip_id}/customers/copy-from/{source_trip_id}",
    response_model=list[TripCustomerRead],
)
def post_copy_trip_customers(
    destination_trip_id: int,
    source_trip_id: int,
    db: Session = Depends(get_db),
) -> list[TripCustomerRead]:
    try:
        return copy_customers_from_trip(
            db,
            destination_trip_id,
            source_trip_id,
        )
    except TripNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )
    except SameTripCopyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination trips must be different.",
        )
