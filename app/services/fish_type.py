from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fish_type import FishType
from app.schemas.fish_type import FishTypeCreate, FishTypeUpdate


class DuplicateFishTypeNameError(Exception):
    pass


class FishTypeNotFoundError(Exception):
    pass


def list_fish_types(db:Session) -> list[FishType]:
    statement =select(FishType).order_by(FishType.id)
    return list(db.scalars(statement).all())

def create_fish_type(db:Session,data:FishTypeCreate):
    fish_type=FishType(name=data.name)
    db.add(fish_type)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateFishTypeNameError from exc

    db.refresh(fish_type)
    return fish_type

def update_fish_type(db:Session,fish_type_id:int,data:FishTypeUpdate):
    fish_type=db.get(FishType,fish_type_id)

    if fish_type is None:
        raise FishTypeNotFoundError

    fish_type.name=data.name

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateFishTypeNameError from exc

    db.refresh(fish_type)
    return fish_type

def deactivate_fish_type(db:Session,fish_type_id:int):
    fish_type=db.get(FishType,fish_type_id)

    if fish_type is None:
        raise FishTypeNotFoundError
    fish_type.is_active = False

    db.commit()
    db.refresh(fish_type)

    return fish_type