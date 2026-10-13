
from app.core.record_spec import FieldSpec, RecordSpec
from app.models.fish_type import FishType
from app.schemas.fish_type import (
    FishTypeCreate,
    FishTypeRead,
    FishTypeUpdate,
)

FISH_TYPE = RecordSpec(
    key="fish-types",
    title="Fish Type",
    model=FishType,
    fields=(
        FieldSpec(
            name="id",
            label="ID",
            in_list=True,
        ),
        FieldSpec(
            name="name",
            label="Name",
            in_list=True,
            searchable=True,
            editable=True,
        ),
        FieldSpec(
            name="is_active",
            label="Active",
            in_list=True,
        ),
    ),
    order_by="id",
    sort_fields=("id", "name", "is_active"),
    operations=frozenset({
        "list",
        "get",
        "create",
        "update",
        "activate",
        "deactivate",
        "delete",
    }),
    create_schema=FishTypeCreate,
    update_schema=FishTypeUpdate,
    read_schema=FishTypeRead,
)
