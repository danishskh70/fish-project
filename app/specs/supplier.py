
from app.core.record_spec import FieldSpec, RecordSpec
from app.models.supplier import Supplier
from app.schemas.supplier import (
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)

SUPPLIER = RecordSpec(
    key="suppliers",
    title="Supplier",
    model=Supplier,
    fields=(
        FieldSpec(
            name="id",
            label="ID",
        ),
        FieldSpec(
            name="name",
            label="Name",
            searchable=True,
            editable=True,
        ),
        FieldSpec(
            name="phone",
            label="Phone",
            searchable=True,
            editable=True,
        ),
        FieldSpec(
            name="address",
            label="Address",
            searchable=True,
            editable=True,
        ),
        FieldSpec(
            name="is_active",
            label="Active",
        ),
    ),
    order_by="id",
    sort_fields=("id", "name", "phone", "address", "is_active"),
    operations=frozenset({
        "list",
        "get",
        "create",
        "update",
        "activate",
        "deactivate",
        "delete",
    }),
    create_schema=SupplierCreate,
    update_schema=SupplierUpdate,
    read_schema=SupplierRead,
)
