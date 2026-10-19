def test_preflight_allows_lovable_origin(client):
    response = client.options(
        "/api/trips/",
        headers={
            "Origin": "https://demo.lovable.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://demo.lovable.app"


def test_preflight_rejects_unknown_origin(client):
    response = client.options(
        "/api/trips/",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers