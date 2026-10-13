from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierNotFoundError(Exception):
    pass


class EmptySupplierUpdateError(Exception):
    pass


def list_suppliers(db: Session) -> list[Supplier]:
    statement = select(Supplier).order_by(Supplier.id)
    return list(db.scalars(statement).all())


def create_supplier(
    db: Session,
    data: SupplierCreate,
) -> Supplier:
    supplier = Supplier(
        name=data.name,
        phone=data.phone,
        address=data.address,
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return supplier


def update_supplier(
    db: Session,
    supplier_id: int,
    data: SupplierUpdate,
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)

    if supplier is None:
        raise SupplierNotFoundError

    changes = data.model_dump(exclude_unset=True, exclude_none=True)

    if not changes:
        raise EmptySupplierUpdateError

    for field, value in changes.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)

    return supplier


def deactivate_supplier(
    db: Session,
    supplier_id: int,
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)

    if supplier is None:
        raise SupplierNotFoundError

    supplier.is_active = False
    db.commit()
    db.refresh(supplier)

    return supplier

def activate_supplier(
    db: Session,
    supplier_id: int,
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)

    if supplier is None:
        raise SupplierNotFoundError

    supplier.is_active = True

    db.commit()
    db.refresh(supplier)

    return supplier