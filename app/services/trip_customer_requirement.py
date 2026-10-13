
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.models.trip_customer import TripCustomer
from app.models.trip_customer_requirement import TripCustomerRequirement
from app.schemas.trip_customer_requirement import (
    TripCustomerRequirementCreate,
    TripCustomerRequirementUpdate,
)


class TripCustomerAssignmentNotFoundError(Exception):
    pass


class FishTypeNotFoundError(Exception):
    pass


class InactiveFishTypeError(Exception):
    pass


class DuplicateRequirementError(Exception):
    pass


class RequirementNotFoundError(Exception):
    pass


def get_trip_customer_assignment(
    db: Session,
    trip_id: int,
    customer_id: int,
) -> TripCustomer:
    assignment = db.scalar(
        select(TripCustomer).where(
            TripCustomer.trip_id == trip_id,
            TripCustomer.customer_id == customer_id,
        )
    )

    if assignment is None:
        raise TripCustomerAssignmentNotFoundError

    return assignment


def create_requirement(
    db: Session,
    trip_id: int,
    customer_id: int,
    data: TripCustomerRequirementCreate,
) -> TripCustomerRequirement:
    assignment = get_trip_customer_assignment(
        db,
        trip_id,
        customer_id,
    )

    fish_type = db.get(FishType, data.fish_type_id)

    if fish_type is None:
        raise FishTypeNotFoundError

    if not fish_type.is_active:
        raise InactiveFishTypeError

    existing = db.scalar(
        select(TripCustomerRequirement).where(
            TripCustomerRequirement.trip_customer_id == assignment.id,
            TripCustomerRequirement.fish_type_id == data.fish_type_id,
        )
    )

    if existing is not None:
        raise DuplicateRequirementError

    requirement = TripCustomerRequirement(
        trip_customer_id=assignment.id,
        fish_type_id=data.fish_type_id,
        quantity_bags=data.quantity_bags,
    )

    db.add(requirement)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateRequirementError from exc

    db.refresh(requirement)
    return requirement


def list_requirements(
    db: Session,
    trip_id: int,
    customer_id: int,
) -> list[TripCustomerRequirement]:
    assignment = get_trip_customer_assignment(
        db,
        trip_id,
        customer_id,
    )

    statement = (
        select(TripCustomerRequirement)
        .where(
            TripCustomerRequirement.trip_customer_id == assignment.id
        )
        .order_by(TripCustomerRequirement.id)
    )

    return list(db.scalars(statement).all())


def update_requirement(
    db: Session,
    trip_id: int,
    customer_id: int,
    requirement_id: int,
    data: TripCustomerRequirementUpdate,
) -> TripCustomerRequirement:
    assignment = get_trip_customer_assignment(
        db,
        trip_id,
        customer_id,
    )

    requirement = db.scalar(
        select(TripCustomerRequirement).where(
            TripCustomerRequirement.id == requirement_id,
            TripCustomerRequirement.trip_customer_id == assignment.id,
        )
    )

    if requirement is None:
        raise RequirementNotFoundError

    requirement.quantity_bags = data.quantity_bags

    db.commit()
    db.refresh(requirement)

    return requirement
