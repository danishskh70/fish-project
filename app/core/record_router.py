
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.record_service import (
    EmptyRecordUpdateError,
    RecordConflictError,
    RecordNotFoundError,
    RecordService,
)
from app.core.record_spec import RecordSpec


def make_record_router(
    spec: RecordSpec,
    service_class: type[RecordService] = RecordService,
) -> APIRouter:
    router = APIRouter(
        prefix=f"/{spec.key}",
        tags=[spec.key],
    )

    if "list" in spec.operations:

        @router.get("/", response_model=list[spec.read_schema])
        def list_records(
            sort_by: str | None = None,
            sort_order: str = "asc",
            search: str | None = None,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            return service.list_records(
                sort_by=sort_by,
                sort_order=sort_order,
                search=search,
            )

    if "get" in spec.operations:

        @router.get(
            "/{record_id}",
            response_model=spec.read_schema,
        )
        def get_record(
            record_id: int,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)
            record = service.get_record(record_id)

            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{spec.title} not found.",
                )

            return record

    if "create" in spec.operations:

        @router.post(
            "/",
            response_model=spec.read_schema,
            status_code=status.HTTP_201_CREATED,
        )
        def create_record(
            data: spec.create_schema,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            try:
                return service.create_record(data)
            except RecordConflictError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"A {spec.title.lower()} with these values "
                        "conflicts with an existing record."
                    ),
                )

    if "update" in spec.operations:

        @router.patch(
            "/{record_id}",
            response_model=spec.read_schema,
        )
        def update_record(
            record_id: int,
            data: spec.update_schema,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            try:
                return service.update_record(record_id, data)
            except RecordNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{spec.title} not found.",
                )
            except EmptyRecordUpdateError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="At least one editable field must be provided.",
                )
            except RecordConflictError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"The {spec.title.lower()} conflicts with "
                        "an existing record."
                    ),
                )

    if "activate" in spec.operations:

        @router.post(
            "/{record_id}/activate",
            response_model=spec.read_schema,
        )
        def activate_record(
            record_id: int,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            try:
                return service.set_active(record_id, True)
            except RecordNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{spec.title} not found.",
                )

    if "deactivate" in spec.operations:

        @router.post(
            "/{record_id}/deactivate",
            response_model=spec.read_schema,
        )
        def deactivate_record(
            record_id: int,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            try:
                return service.set_active(record_id, False)
            except RecordNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{spec.title} not found.",
                )

    if "delete" in spec.operations:

        @router.delete(
            "/{record_id}",
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def delete_record(
            record_id: int,
            db: Session = Depends(get_db),
        ):
            service = service_class(db, spec)

            try:
                service.delete_record(record_id)
            except RecordNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{spec.title} not found.",
                )
            except RecordConflictError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"The {spec.title.lower()} cannot be deleted "
                        "because it is referenced by other records."
                    ),
                )


    return router
