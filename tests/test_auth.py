from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_token
from app.models.owner_session import OwnerSession
from app.services.owner import create_owner, reset_password

PASSWORD = "correct horse battery"

@pytest.fixture
def client(raw_client):
    return raw_client

@pytest.fixture(autouse=True)
def plain_http_cookie(monkeypatch):
    # TestClient talks plain http. A Secure cookie would never be sent back.
    monkeypatch.setattr(settings, "session_cookie_secure", False)


@pytest.fixture
def owner(db_session):
    return create_owner(db_session, "danish", PASSWORD)


def do_login(client, password=PASSWORD, username="danish", **extra):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password, **extra},
    )


def edit_session(session_factory, **values):
    with session_factory() as db:
        row = db.scalars(select(OwnerSession)).one()
        for key, value in values.items():
            setattr(row, key, value)
        db.commit()


def test_login_sets_httponly_cookie(client, owner):
    response = do_login(client)
    assert response.status_code == 200, response.text
    assert response.json() == {"username": "danish", "token": None}
    cookie = response.headers["set-cookie"].lower()
    assert f"{settings.session_cookie_name}=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert response.headers["cache-control"] == "no-store"


def test_wrong_password_rejected(client, owner):
    response = do_login(client, password="not the password")
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_unknown_user_gives_same_answer_as_wrong_password(client, owner):
    wrong_password = do_login(client, password="not the password")
    unknown_user = do_login(client, username="nobody")
    assert unknown_user.status_code == wrong_password.status_code == 401
    assert unknown_user.json() == wrong_password.json()


def test_me_without_login_is_401(client, owner):
    assert client.get("/api/auth/me").status_code == 401


def test_me_after_login(client, owner):
    do_login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"username": "danish"}


def test_logout_ends_the_session(client, owner, test_session_local):
    do_login(client)
    assert client.post("/api/auth/logout").status_code == 204
    with test_session_local() as db:
        assert db.scalars(select(OwnerSession)).all() == []
    assert client.get("/api/auth/me").status_code == 401


def test_logout_without_login_is_fine(client, owner):
    assert client.post("/api/auth/logout").status_code == 204


def test_token_in_body_works_as_bearer(client, owner):
    response = do_login(client, token_in_body=True)
    token = response.json()["token"]
    assert token

    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    ok = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert ok.status_code == 200


def test_garbage_bearer_rejected(client, owner):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer nonsense"}
    )
    assert response.status_code == 401


def test_database_keeps_only_the_token_hash(client, owner, test_session_local):
    response = do_login(client, token_in_body=True)
    token = response.json()["token"]
    with test_session_local() as db:
        row = db.scalars(select(OwnerSession)).one()
    assert row.token_hash == hash_token(token)
    assert row.token_hash != token
    assert token not in row.token_hash


def test_absolute_expiry(client, owner, test_session_local):
    do_login(client)
    edit_session(
        test_session_local,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    assert client.get("/api/auth/me").status_code == 401
    with test_session_local() as db:
        assert db.scalars(select(OwnerSession)).all() == []


def test_idle_expiry(client, owner, test_session_local):
    do_login(client)
    edit_session(
        test_session_local,
        last_seen_at=datetime.now(UTC)
        - timedelta(hours=settings.session_idle_hours + 1),
    )
    assert client.get("/api/auth/me").status_code == 401


def test_password_reset_signs_out_every_session(client, owner, db_session):
    do_login(client)
    reset_password(db_session, "danish", "another long password")
    assert client.get("/api/auth/me").status_code == 401
    assert do_login(client, password=PASSWORD).status_code == 401
    assert do_login(client, password="another long password").status_code == 200


def test_overlong_password_rejected_before_hashing(client, owner):
    response = do_login(client, password="x" * 2000)
    assert response.status_code == 422