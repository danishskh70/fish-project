def preflight(client, origin):
    return client.options(
        "/api/trips/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_preflight_allows_listed_origin_with_credentials(client):
    response = preflight(client, "http://localhost:5173")
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_rejects_unknown_origin(client):
    response = preflight(client, "https://evil.example.com")
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_lovable_wildcard_is_gone(client):
    response = preflight(client, "https://anything.lovable.app")
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers