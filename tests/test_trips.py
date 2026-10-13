from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.trip_fish_type import TripFishType


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

def create_fish_type(
    client: TestClient,
    *,
    active: bool = True,
    name: str = "Test Rohu",
) -> int:
    response = client.post(
        "/api/fish-types/",
        json={"name": name},
    )
    assert response.status_code == 201, response.text

    fish_type_id = response.json()["id"]

    if not active:
        response = client.post(
            f"/api/fish-types/{fish_type_id}/deactivate"
        )
        assert response.status_code == 200, response.text

    return fish_type_id

def test_create_trip(client: TestClient) -> None:
    supplier_id = create_supplier(client)
    fish_type_id = create_fish_type(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id],
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
    first_fish_type_id = create_fish_type(client)
    second_fish_type_id = client.post(
        "/api/fish-types/",
        json={"name": "Test Katla"},
    ).json()["id"]

    first_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-12",
            "supplier_id": supplier_id,
            "fish_type_ids": [first_fish_type_id],
        },
    )
    second_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [second_fish_type_id],
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
    fish_type_id = create_fish_type(client)

    create_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id],
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
    fish_type_id = create_fish_type(client)
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": 999999,
            "fish_type_ids": [fish_type_id],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Supplier not found."


def test_create_trip_with_inactive_supplier(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client, active=False)
    fish_type_id = create_fish_type(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id],
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

def test_create_trip_with_nonexistent_fish_type(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [999999],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Fish type 999999 not found."


def test_create_trip_with_inactive_fish_type(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)
    fish_type_id = create_fish_type(client, active=False)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Cannot add inactive fish type {fish_type_id} to a trip."
    )


def test_failed_trip_creation_does_not_create_trip(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)
    fish_type_id = create_fish_type(client)

    failed_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id, 999999],
        },
    )

    assert failed_response.status_code == 400

    list_response = client.get("/api/trips/")

    assert list_response.status_code == 200
    assert list_response.json() == []

def test_create_trip_saves_selected_fish_types(
    client: TestClient,
    db_session,
) -> None:
    supplier_id = create_supplier(client)
    first_fish_type_id = create_fish_type(client)

    second_response = client.post(
        "/api/fish-types/",
        json={"name": "Test Katla"},
    )
    assert second_response.status_code == 201, second_response.text
    second_fish_type_id = second_response.json()["id"]

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [
                first_fish_type_id,
                second_fish_type_id,
            ],
        },
    )
    assert response.status_code == 201, response.text

    trip_id = response.json()["id"]

    saved_fish_type_ids = db_session.scalars(
        select(TripFishType.fish_type_id).where(
            TripFishType.trip_id == trip_id
        )
    ).all()

    assert set(saved_fish_type_ids) == {
        first_fish_type_id,
        second_fish_type_id,
    }

def test_add_fish_type_to_trip(client: TestClient) -> None:
    supplier_id = create_supplier(client)
    initial_fish_type_id = create_fish_type(client)

    trip_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [initial_fish_type_id],
        },
    )
    assert trip_response.status_code == 201, trip_response.text
    trip_id = trip_response.json()["id"]

    new_fish_type_response = client.post(
        "/api/fish-types/",
        json={"name": "Test Catla"},
    )
    assert new_fish_type_response.status_code == 201
    new_fish_type_id = new_fish_type_response.json()["id"]

    response = client.post(
        f"/api/trips/{trip_id}/fish-types",
        json={"fish_type_id": new_fish_type_id},
    )

    assert response.status_code == 201, response.text
    assert response.json()["trip_id"] == trip_id
    assert response.json()["fish_type_id"] == new_fish_type_id


def test_add_fish_type_to_nonexistent_trip(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client)

    response = client.post(
        "/api/trips/999999/fish-types",
        json={"fish_type_id": fish_type_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_add_nonexistent_fish_type_to_trip(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)
    initial_fish_type_id = create_fish_type(client)

    trip_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [initial_fish_type_id],
        },
    )
    assert trip_response.status_code == 201, trip_response.text
    trip_id = trip_response.json()["id"]

    response = client.post(
        f"/api/trips/{trip_id}/fish-types",
        json={"fish_type_id": 999999},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Fish type not found."


def test_add_inactive_fish_type_to_trip(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)
    initial_fish_type_id = create_fish_type(client)

    trip_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [initial_fish_type_id],
        },
    )
    assert trip_response.status_code == 201, trip_response.text
    trip_id = trip_response.json()["id"]

    inactive_fish_type_id = create_fish_type(
        client,
        active=False,
        name="Test Inactive Rohu",
    )

    response = client.post(
        f"/api/trips/{trip_id}/fish-types",
        json={"fish_type_id": inactive_fish_type_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot add an inactive fish type to a trip."
    )


def test_add_duplicate_fish_type_to_trip(
    client: TestClient,
) -> None:
    supplier_id = create_supplier(client)
    fish_type_id = create_fish_type(client)

    trip_response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
            "fish_type_ids": [fish_type_id],
        },
    )
    assert trip_response.status_code == 201, trip_response.text
    trip_id = trip_response.json()["id"]

    response = client.post(
        f"/api/trips/{trip_id}/fish-types",
        json={"fish_type_id": fish_type_id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Fish type is already configured for this trip."
    )