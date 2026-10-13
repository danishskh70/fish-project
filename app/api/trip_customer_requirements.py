
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.trip_customer_requirement import (
    TripCustomerRequirementCreate,
    TripCustomerRequirementRead,
    TripCustomerRequirementUpdate,
)
from app.services.trip_customer_requirement import (
    DuplicateRequirementError,
    FishTypeNotFoundError,
    InactiveFishTypeError,
    RequirementNotFoundError,
    TripCustomerAssignmentNotFoundError,
    create_requirement,
    list_requirements,
    update_requirement,
)


router = APIRouter(
    prefix="/trips",
    tags=["Trip Customer Requirements"],
)


@router.post(
    "/{trip_id}/customers/{customer_id}/requirements",
    response_model=TripCustomerRequirementRead,
    status_code=status.HTTP_201_CREATED,
)
def post_requirement(
    trip_id: int,
    customer_id: int,
    data: TripCustomerRequirementCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_requirement(db, trip_id, customer_id, data)
    except TripCustomerAssignmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Customer is not assigned to this trip.",
        )
    except FishTypeNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Fish type not found.",
        )
    except InactiveFishTypeError:
        raise HTTPException(
            status_code=400,
            detail="Cannot add a requirement for an inactive fish type.",
        )
    except DuplicateRequirementError:
        raise HTTPException(
            status_code=409,
            detail="A requirement for this fish type already exists.",
        )


@router.get(
    "/{trip_id}/customers/{customer_id}/requirements",
    response_model=list[TripCustomerRequirementRead],
)
def get_requirements(
    trip_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
):
    try:
        return list_requirements(db, trip_id, customer_id)
    except TripCustomerAssignmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Customer is not assigned to this trip.",
        )


@router.patch(
    "/{trip_id}/customers/{customer_id}/requirements/{requirement_id}",
    response_model=TripCustomerRequirementRead,
)
def patch_requirement(
    trip_id: int,
    customer_id: int,
    requirement_id: int,
    data: TripCustomerRequirementUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_requirement(
            db,
            trip_id,
            customer_id,
            requirement_id,
            data,
        )
    except TripCustomerAssignmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Customer is not assigned to this trip.",
        )
    except RequirementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Requirement not found for this customer and trip.",
        )
