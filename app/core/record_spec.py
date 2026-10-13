
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    in_list: bool = True
    searchable: bool = False
    editable: bool = False


@dataclass(frozen=True)
class RecordSpec:
    key: str
    title: str
    model: type[DeclarativeBase]
    fields: tuple[FieldSpec, ...]
    order_by: str
    sort_fields: tuple[str, ...]
    operations: frozenset[str]

    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    read_schema: type[BaseModel]

    @property
    def table(self) -> Any:
        return self.model.__table__

    @property
    def search_fields(self) -> tuple[str, ...]:
        return tuple(
            field.name
            for field in self.fields
            if field.searchable
        )
