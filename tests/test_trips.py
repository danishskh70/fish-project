from fastapi.testclient import TestClient


def create_supplier(client: TestClient, *, active: bool = True) -> int:
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Test Supplier",
            "phone": "9876543210",
            "address": "Test Address",
        },
    )
    assert response.status_code == 201, response.text

    supplier_id = response.json()["id"]

    if not active:
        response = client.post(
            f"/api/suppliers/{supplier_id}/deactivate"
        )
        assert response.status_code in (200, 204), response.text

    return supplier_id


def test_create_trip(client: TestClient) -> None:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["id"] is not None
    assert data["trip_date"] == "2026-10-13"
    assert data["supplier_id"] == supplier_id
    assert data["status"] == "PLANNING"
    assert data["created_at"] is not None


def test_list_trips(client: TestClient) -> None:
    supplier_id = create_supplier(client)

    first_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-12",
            "supplier_id": supplier_id,
        },
    )
    second_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
        },
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text

    response = client.get("/api/trips/")

    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data) == 2
    assert data[0]["trip_date"] == "2026-10-13"
    assert data[1]["trip_date"] == "2026-10-12"


def test_get_trip(client: TestClient) -> None:
    supplier_id = create_supplier(client)

    create_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
        },
    )
    assert create_response.status_code == 201, create_response.text

    trip_id = create_response.json()["id"]

    response = client.get(f"/api/trips/{trip_id}")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == trip_id
    assert response.json()["supplier_id"] == supplier_id


def test_get_nonexistent_trip(client: TestClient) -> None:
    response = client.get("/api/trips/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_create_trip_with_nonexistent_supplier(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": 999999,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Supplier not found."


def test_create_trip_with_inactive_supplier(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client, active=False)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot create a trip with an inactive supplier."
    )


def test_create_trip_with_invalid_data(client: TestClient) -> None:
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "not-a-date",
            "supplier_id": 1,
        },
    )

    assert response.status_code == 422


def test_create_trip_with_invalid_supplier_id(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": 0,
        },
    )

    assert response.status_code == 422
