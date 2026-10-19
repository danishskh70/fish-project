import pytest


@pytest.mark.parametrize("path", ["/api/trips/", "/api/auth/login"])
def test_foreign_origin_write_is_blocked(raw_client, path):
    response = raw_client.post(
        path, json={}, headers={"Origin": "https://evil.example.com"}
    )
    assert response.status_code == 403


def test_null_origin_is_blocked(raw_client):
    response = raw_client.post(
        "/api/trips/", json={}, headers={"Origin": "null"}
    )
    assert response.status_code == 403


def test_listed_origin_gets_through_to_login_check(raw_client):
    response = raw_client.post(
        "/api/trips/", json={}, headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 401


def test_no_origin_header_gets_through(raw_client):
    assert raw_client.post("/api/trips/", json={}).status_code == 401


def test_same_origin_gets_through(raw_client):
    response = raw_client.post(
        "/api/trips/", json={}, headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 401


def test_foreign_origin_read_is_not_blocked_here(raw_client):
    response = raw_client.get(
        "/api/health", headers={"Origin": "https://evil.example.com"}
    )
    assert response.status_code == 200