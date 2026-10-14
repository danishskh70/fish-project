
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.fish_type import FishType
from app.models.trip import Trip
from app.models.trip_customer import TripCustomer
from app.models.trip_customer_requirement import TripCustomerRequirement
from app.models.trip_fish_type import TripFishType
from app.schemas.trip_requirements_table import (
    RequirementsTableCustomer,
    RequirementsTableFishTotal,
    RequirementsTableFishType,
    RequirementsTableQuantity,
    TripRequirementsTableRead,
)


class TripRequirementsTableNotFoundError(Exception):
    pass


def get_trip_requirements_table(
    db: Session,
    trip_id: int,
) -> TripRequirementsTableRead:
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise TripRequirementsTableNotFoundError

    
    fish_type_rows = db.execute(
        select(
            FishType.id,
            FishType.name,
            TripFishType.planned_quantity_bags,
        )
        .join(
            TripFishType,
            TripFishType.fish_type_id == FishType.id,
        )
        .where(TripFishType.trip_id == trip_id)
        .order_by(TripFishType.id)
    ).all()


    
    fish_types = [
        RequirementsTableFishType(id=row.id, name=row.name)
        for row in fish_type_rows
    ]
    planned_quantities_by_id = {
        row.id: row.planned_quantity_bags
        for row in fish_type_rows
    }

    customer_rows = db.execute(
        select(
            TripCustomer.id.label("trip_customer_id"),
            Customer.id.label("customer_id"),
            Customer.name,
            Customer.phone,
            Customer.address,
        )
        .join(
            Customer,
            Customer.id == TripCustomer.customer_id,
        )
        .where(TripCustomer.trip_id == trip_id)
        .order_by(TripCustomer.id)
    ).all()

    requirement_rows = db.execute(
        select(
            TripCustomerRequirement.trip_customer_id,
            TripCustomerRequirement.fish_type_id,
            TripCustomerRequirement.quantity_bags,
        )
        .join(
            TripCustomer,
            TripCustomer.id
            == TripCustomerRequirement.trip_customer_id,
        )
        .where(TripCustomer.trip_id == trip_id)
    ).all()

    saved_quantities = {
        (row.trip_customer_id, row.fish_type_id): row.quantity_bags
        for row in requirement_rows
    }

    customers = []
    fish_totals_by_id = {
        fish_type.id: 0 for fish_type in fish_types
    }
    grand_total_bags = 0

    for row in customer_rows:
        quantities = []
        customer_total_bags = 0

        for fish_type in fish_types:
            quantity_bags = saved_quantities.get(
                (row.trip_customer_id, fish_type.id),
                0,
            )

            quantities.append(
                RequirementsTableQuantity(
                    fish_type_id=fish_type.id,
                    quantity_bags=quantity_bags,
                )
            )

            customer_total_bags += quantity_bags
            fish_totals_by_id[fish_type.id] += quantity_bags

        customers.append(
            RequirementsTableCustomer(
                trip_customer_id=row.trip_customer_id,
                customer_id=row.customer_id,
                name=row.name,
                phone=row.phone,
                address=row.address,
                quantities=quantities,
                total_bags=customer_total_bags,
            )
        )

        grand_total_bags += customer_total_bags

    
    fish_totals = []

    for fish_type in fish_types:
        demand_bags = fish_totals_by_id[fish_type.id]
        planned_quantity_bags = planned_quantities_by_id[fish_type.id]

        effective_planned_quantity_bags = (
            planned_quantity_bags
            if planned_quantity_bags is not None
            else demand_bags
        )

        shortfall_bags = max(
            0,
            demand_bags - effective_planned_quantity_bags,
        )

        fish_totals.append(
            RequirementsTableFishTotal(
                fish_type_id=fish_type.id,
                quantity_bags=demand_bags,
                planned_quantity_bags=planned_quantity_bags,
                effective_planned_quantity_bags=effective_planned_quantity_bags,
                shortfall_bags=shortfall_bags,
                shortfall_exists=shortfall_bags > 0,
            )
        )


    return TripRequirementsTableRead(
        trip_id=trip.id,
        fish_types=fish_types,
        customers=customers,
        fish_totals=fish_totals,
        grand_total_bags=grand_total_bags,
    )
