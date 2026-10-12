from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.db.session import SessionLocal
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.customer import (
    CustomerNotFoundError,
    create_customer,
    deactivate_customer,
    list_customers,
    update_customer,
)


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/", response_model=list[CustomerRead])
def get_customers(db: Session = Depends(get_db)):
    return list_customers(db)


@router.post(
    "/",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
)
def post_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
):
    return create_customer(db, data)


@router.patch("/{customer_id}", response_model=CustomerRead)
def patch_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_customer(db, customer_id, data)
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )


@router.post("/{customer_id}/deactivate", response_model=CustomerRead)
def post_deactivate_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    try:
        return deactivate_customer(db, customer_id)
    except CustomerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
