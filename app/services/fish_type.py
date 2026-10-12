from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.schemas.fish_type import FishTypeCreate, FishTypeUpdate


class DuplicateFishTypeNameError(Exception):
    pass


class FishTypeNotFoundError(Exception):
    pass


def list_fish_types(db: Session) -> list[FishType]:
    statement = select(FishType).order_by(FishType.id)
    return list(db.scalars(statement).all())


def _is_duplicate_name(
    db: Session,
    name: str,
    exclude_id: int | None = None,
) -> bool:
    statement = select(FishType.id).where(FishType.name == name)

    if exclude_id is not None:
        statement = statement.where(FishType.id != exclude_id)

    return db.scalar(statement) is not None


def create_fish_type(
    db: Session,
    data: FishTypeCreate,
) -> FishType:
    fish_type = FishType(name=data.name)
    db.add(fish_type)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if _is_duplicate_name(db, data.name):
            raise DuplicateFishTypeNameError from exc

        raise

    db.refresh(fish_type)
    return fish_type


def update_fish_type(
    db: Session,
    fish_type_id: int,
    data: FishTypeUpdate,
) -> FishType:
    fish_type = db.get(FishType, fish_type_id)

    if fish_type is None:
        raise FishTypeNotFoundError

    fish_type.name = data.name

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if _is_duplicate_name(
            db,
            data.name,
            exclude_id=fish_type_id,
        ):
            raise DuplicateFishTypeNameError from exc

        raise

    db.refresh(fish_type)
    return fish_type


def deactivate_fish_type(
    db: Session,
    fish_type_id: int,
) -> FishType:
    fish_type = db.get(FishType, fish_type_id)

    if fish_type is None:
        raise FishTypeNotFoundError

    fish_type.is_active = False
    db.commit()
    db.refresh(fish_type)

    return fish_type