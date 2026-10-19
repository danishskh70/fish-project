from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    needs_rehash,
    new_token,
    verify_password,
)
from app.models.owner import Owner
from app.models.owner_session import OwnerSession

TOUCH_AFTER = timedelta(seconds=60)
MAX_TOKEN_LENGTH = 200


class InvalidCredentialsError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes. Treat them as UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def login(db: Session, username: str, password: str) -> tuple[Owner, str]:
    owner = db.scalar(select(Owner).where(Owner.username == username.strip()))

    # Always verify, even for an unknown user, so timing does not differ.
    stored_hash = owner.password_hash if owner is not None else DUMMY_HASH
    password_ok = verify_password(stored_hash, password)
    if owner is None or not password_ok:
        raise InvalidCredentialsError

    now = _now()
    token = new_token()
    try:
        if needs_rehash(owner.password_hash):
            owner.password_hash = hash_password(password)
        db.execute(
            delete(OwnerSession).where(
                OwnerSession.owner_id == owner.id,
                OwnerSession.expires_at < now,
            )
        )
        db.add(
            OwnerSession(
                owner_id=owner.id,
                token_hash=hash_token(token),
                last_seen_at=now,
                expires_at=now + timedelta(days=settings.session_absolute_days),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return owner, token


def get_owner_for_token(db: Session, token: str | None) -> Owner | None:
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None

    session = db.scalar(
        select(OwnerSession).where(OwnerSession.token_hash == hash_token(token))
    )
    if session is None:
        return None

    now = _now()
    last_seen = _aware(session.last_seen_at)
    idle_limit = last_seen + timedelta(hours=settings.session_idle_hours)
    if now >= _aware(session.expires_at) or now >= idle_limit:
        db.delete(session)
        db.commit()
        return None

    if now - last_seen > TOUCH_AFTER:
        session.last_seen_at = now
        db.commit()

    return db.get(Owner, session.owner_id)


def logout(db: Session, token: str) -> None:
    db.execute(
        delete(OwnerSession).where(OwnerSession.token_hash == hash_token(token))
    )
    db.commit()