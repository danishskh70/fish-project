import pytest

from app.core.config import settings
from app.core.throttle import LoginThrottle
from app.services.owner import create_owner

PASSWORD = "correct horse battery"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def throttle(clock):
    return LoginThrottle(clock=clock)


# ---------- unit ----------

def test_locks_after_max_failures(throttle):
    for _ in range(4):
        throttle.record_failure("ip:1", 5, 900)
    assert throttle.retry_after("ip:1") == 0
    throttle.record_failure("ip:1", 5, 900)
    assert 0 < throttle.retry_after("ip:1") <= 901


def test_lock_ends_after_the_wait(throttle, clock):
    for _ in range(5):
        throttle.record_failure("ip:1", 5, 900)
    clock.now += 901
    assert throttle.retry_after("ip:1") == 0
    # fresh start: one failure does not lock again
    throttle.record_failure("ip:1", 5, 900)
    assert throttle.retry_after("ip:1") == 0


def test_old_failures_do_not_count(throttle, clock):
    for _ in range(4):
        throttle.record_failure("ip:1", 5, 900)
    clock.now += 901
    throttle.record_failure("ip:1", 5, 900)
    assert throttle.retry_after("ip:1") == 0


def test_keys_are_separate(throttle):
    for _ in range(5):
        throttle.record_failure("ip:1", 5, 900)
    assert throttle.retry_after("ip:1") > 0
    assert throttle.retry_after("ip:2") == 0


def test_reset_clears_the_count(throttle):
    for _ in range(4):
        throttle.record_failure("ip:1", 5, 900)
    throttle.reset("ip:1")
    throttle.record_failure("ip:1", 5, 900)
    assert throttle.retry_after("ip:1") == 0


# ---------- through the API ----------

@pytest.fixture
def owner(db_session):
    return create_owner(db_session, "danish", PASSWORD)


def attempt(raw_client, password, username="danish"):
    return raw_client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def test_sixth_wrong_try_is_locked_even_with_right_password(raw_client, owner):
    for _ in range(settings.login_max_failures):
        assert attempt(raw_client, "wrong password!!").status_code == 401
    locked = attempt(raw_client, PASSWORD)
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0
    assert "set-cookie" not in locked.headers


def test_success_resets_the_count(raw_client, owner, monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    for _ in range(settings.login_max_failures - 1):
        attempt(raw_client, "wrong password!!")
    assert attempt(raw_client, PASSWORD).status_code == 200
    for _ in range(settings.login_max_failures - 1):
        assert attempt(raw_client, "wrong password!!").status_code == 401


def test_unknown_user_tries_are_counted_too(raw_client, owner):
    for _ in range(settings.login_max_failures):
        attempt(raw_client, "whatever password", username="nobody")
    assert attempt(raw_client, PASSWORD).status_code == 429