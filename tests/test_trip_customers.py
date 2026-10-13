from fastapi.testclient import TestClient


def create_supplier(client: TestClient) -> int:
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Test Supplier",
            "phone": "9876543210",
            "address": "Test Address",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_customer(client: TestClient, *, active: bool = True) -> int:
    response = client.post(
        "/api/customers/",
        json={
            "name": "Test Customer",
            "phone": "9876543211",
            "address": "Test Address",
        },
    )
    assert response.status_code == 201, response.text

    customer_id = response.json()["id"]

    if not active:
        response = client.post(
            f"/api/customers/{customer_id}/deactivate"
        )
        assert response.status_code in (200, 204), response.text

    return customer_id


def create_trip(client: TestClient) -> int:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_add_customer_to_trip(client: TestClient) -> None:
    trip_id = create_trip(client)
    customer_id = create_customer(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": customer_id},
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["id"] is not None
    assert data["trip_id"] == trip_id
    assert data["customer_id"] == customer_id
    assert data["created_at"] is not None


def test_list_trip_customers(client: TestClient) -> None:
    trip_id = create_trip(client)
    first_customer_id = create_customer(client)
    second_customer_id = create_customer(client)

    for customer_id in (first_customer_id, second_customer_id):
        response = client.post(
            f"/api/trips/{trip_id}/customers",
            json={"customer_id": customer_id},
        )
        assert response.status_code == 201, response.text

    response = client.get(f"/api/trips/{trip_id}/customers")

    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data) == 2
    assert [item["customer_id"] for item in data] == [
        first_customer_id,
        second_customer_id,
    ]


def test_cannot_assign_same_customer_twice(
    client: TestClient,
) -> None:
    trip_id = create_trip(client)
    customer_id = create_customer(client)

    first_response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": customer_id},
    )
    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": customer_id},
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Customer is already assigned to this trip."
    )


def test_cannot_assign_customer_to_nonexistent_trip(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/api/trips/999999/customers",
        json={"customer_id": customer_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_cannot_assign_nonexistent_customer(
    client: TestClient,
) -> None:
    trip_id = create_trip(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found."


def test_cannot_assign_inactive_customer(
    client: TestClient,
) -> None:
    trip_id = create_trip(client)
    customer_id = create_customer(client, active=False)

    response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": customer_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot assign an inactive customer to a trip."
    )


def test_list_customers_for_nonexistent_trip(
    client: TestClient,
) -> None:
    response = client.get("/api/trips/999999/customers")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_assign_customer_with_invalid_id(
    client: TestClient,
) -> None:
    trip_id = create_trip(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": 0},
    )

    assert response.status_code == 422
