import re

import pytest

from main import app

OPEN = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
}
METHODS = {"get", "post", "put", "patch", "delete"}


def all_routes():
    routes = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api"):
            continue
        for method in operations:
            if method in METHODS:
                routes.append((method.upper(), path))
    return sorted(routes)


def test_route_list_is_not_empty():
    routes = all_routes()
    assert len(routes) > 40
    assert ("POST", "/api/trips/{trip_id}/close") in routes


@pytest.mark.parametrize(
    "method,path",
    [route for route in all_routes() if route not in OPEN],
)
def test_every_route_needs_login(raw_client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)
    response = raw_client.request(method, url, json={})
    assert response.status_code == 401, f"{method} {path} is not guarded"


@pytest.mark.parametrize("method,path", sorted(OPEN))
def test_open_routes_stay_open(raw_client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)
    response = raw_client.request(method, url, json={})
    assert response.status_code != 401


def test_allowlist_has_no_stale_entries():
    assert OPEN <= set(all_routes())