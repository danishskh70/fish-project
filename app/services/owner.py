from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.owner import Owner
from app.models.owner_session import OwnerSession

MIN_PASSWORD_LENGTH = 12


class OwnerExistsError(Exception):
    pass


class WeakPasswordError(ValueError):
    pass


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )


def create_owner(db: Session, username: str, password: str) -> Owner:
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be blank.")
    _check_password(password)

    if db.scalar(select(Owner.id).limit(1)) is not None:
        raise OwnerExistsError("An owner already exists.")

    owner = Owner(username=username, password_hash=hash_password(password))
    try:
        db.add(owner)
        db.commit()
        db.refresh(owner)
    except Exception:
        db.rollback()
        raise
    return owner


def reset_password(db: Session, username: str, password: str) -> None:
    _check_password(password)

    owner = db.scalar(select(Owner).where(Owner.username == username.strip()))
    if owner is None:
        raise LookupError("Owner not found.")

    try:
        owner.password_hash = hash_password(password)
        # A new password signs out every device.
        db.execute(
            delete(OwnerSession).where(OwnerSession.owner_id == owner.id)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise