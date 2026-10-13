
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.record_spec import RecordSpec


class RecordNotFoundError(Exception):
    """Raised when the requested record does not exist."""


class RecordConflictError(Exception):
    """Raised when a record conflicts with a database constraint."""


class EmptyRecordUpdateError(Exception):
    """Raised when an update contains no editable changes."""


class RecordService:
    def __init__(self, db: Session, spec: RecordSpec) -> None:
        self.db = db
        self.spec = spec
        self.model = spec.model

    def list_records(
        self,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> list:
        if sort_by not in self.spec.sort_fields:
            sort_by = self.spec.order_by

        sort_column = getattr(self.model, sort_by)

        if sort_order.lower() == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        statement = select(self.model)
        search_term = search.strip() if search else ""

        if search_term and self.spec.search_fields:
            escaped_search = (
                search_term
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )

            conditions = [
                getattr(self.model, field).ilike(
                    f"%{escaped_search}%",
                    escape="\\",
                )
                for field in self.spec.search_fields
            ]

            statement = statement.where(or_(*conditions))

        statement = statement.order_by(sort_column)
        return list(self.db.scalars(statement).all())

    def get_record(self, record_id: int):
        return self.db.get(self.model, record_id)

    def create_record(self, data: BaseModel):
        record = self.model(**data.model_dump())
        self.db.add(record)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise RecordConflictError from exc

        self.db.refresh(record)
        return record

    def update_record(self, record_id: int, data: BaseModel):
        record = self.get_record(record_id)

        if record is None:
            raise RecordNotFoundError

        supplied_changes = data.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        editable_fields = {
            field.name
            for field in self.spec.fields
            if field.editable
        }

        changes = {
            name: value
            for name, value in supplied_changes.items()
            if name in editable_fields
        }

        if not changes:
            raise EmptyRecordUpdateError

        for name, value in changes.items():
            setattr(record, name, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise RecordConflictError from exc

        self.db.refresh(record)
        return record

    def set_active(self, record_id: int, is_active: bool):
        record = self.get_record(record_id)

        if record is None:
            raise RecordNotFoundError

        if not hasattr(record, "is_active"):
            raise AttributeError(
                f"{self.model.__name__} does not support activation."
            )

        record.is_active = is_active

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise RecordConflictError from exc

        self.db.refresh(record)
        return record

    def delete_record(self, record_id: int) -> None:
        record = self.get_record(record_id)

        if record is None:
            raise RecordNotFoundError

        try:
            self.db.delete(record)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise RecordConflictError from exc
