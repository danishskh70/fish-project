
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.trip import TripCreate, TripFishTypeAdd, TripRead
from app.services.trip import (
    add_fish_type_to_trip,
    create_trip,
    get_trip,
    list_trips,
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