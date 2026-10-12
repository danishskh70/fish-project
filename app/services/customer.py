from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerNotFoundError(Exception):
    pass


def list_customers(db: Session) -> list[Customer]:
    statement = select(Customer).order_by(Customer.id)
    return list(db.scalars(statement).all())


def create_customer(
    db: Session,
    data: CustomerCreate,
) -> Customer:
    customer = Customer(
        name=data.name,
        phone=data.phone,
        address=data.address,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


def update_customer(
    db: Session,
    customer_id: int,
    data: CustomerUpdate,
) -> Customer:
    customer = db.get(Customer, customer_id)

    if customer is None:
        raise CustomerNotFoundError

    changes = data.model_dump(exclude_unset=True, exclude_none=True)

    for field, value in changes.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    return customer


def deactivate_customer(
    db: Session,
    customer_id: int,
) -> Customer:
    customer = db.get(Customer, customer_id)

    if customer is None:
        raise CustomerNotFoundError

    customer.is_active = False
    db.commit()
    db.refresh(customer)

    return customer