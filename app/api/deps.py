from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.owner import Owner
from app.services.auth import get_owner_for_token

bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name=settings.session_cookie_name, auto_error=False)


def get_db() -> Generator[Session]:
    with SessionLocal() as db:
        yield db


def get_session_token(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    cookie: str | None = Depends(cookie_scheme),
) -> str | None:
    if bearer is not None and bearer.credentials.strip():
        return bearer.credentials.strip()
    return cookie


def require_owner(
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> Owner:
    owner = get_owner_for_token(db, token)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return owner