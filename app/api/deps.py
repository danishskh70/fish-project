from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.owner import Owner
from app.services.auth import get_owner_for_token


def get_db() -> Generator[Session]:
    with SessionLocal() as db:
        yield db


def get_session_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return request.cookies.get(settings.session_cookie_name)


def require_owner(
    request: Request,
    db: Session = Depends(get_db),
) -> Owner:
    owner = get_owner_for_token(db, get_session_token(request))
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return owner