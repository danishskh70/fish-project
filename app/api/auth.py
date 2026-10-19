from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_session_token, require_owner
from app.core.config import settings
from app.core.throttle import login_throttle
from app.models.owner import Owner
from app.schemas.auth import LoginRead, LoginRequest, MeRead
from app.services.auth import InvalidCredentialsError, login, logout

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginRead)
def login_endpoint(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginRead:
    ip_key = f"ip:{request.client.host if request.client else 'unknown'}"
    user_key = f"user:{data.username.strip().lower()}"

    wait = max(
        login_throttle.retry_after(ip_key),
        login_throttle.retry_after(user_key),
    )
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )

    try:
        owner, token = login(db, data.username, data.password)
    except InvalidCredentialsError:
        lock_seconds = settings.login_lock_minutes * 60
        login_throttle.record_failure(
            ip_key, settings.login_max_failures, lock_seconds
        )
        login_throttle.record_failure(
            user_key, settings.login_max_failures_per_user, lock_seconds
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from None

    login_throttle.reset(ip_key)
    login_throttle.reset(user_key)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_absolute_days * 24 * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginRead(
        username=owner.username,
        token=token if data.token_in_body else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(
    response: Response,
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> None:
    if token:
        logout(db, token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )

@router.get("/me", response_model=MeRead)
def me_endpoint(owner: Owner = Depends(require_owner)) -> MeRead:
    return MeRead(username=owner.username)