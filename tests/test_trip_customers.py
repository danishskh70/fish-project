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

def create_fish_type(client: TestClient) -> int:
    response = client.get("/api/fish-types/")
    assert response.status_code == 200, response.text

    fish_types = response.json()

    if fish_types:
        return fish_types[0]["id"]

    response = client.post(
        "/api/fish-types/",
        json={"name": "Test Rohu"},
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

def test_copy_customers_skips_existing_assignments(
    client: TestClient,
) -> None:
    source_trip_id = create_trip(client)
    destination_trip_id = create_trip(client)

    first_customer_id = create_customer(client)
    second_customer_id = create_customer(client)
    third_customer_id = create_customer(client)

    # Source trip has all three customers.
    for customer_id in (
        first_customer_id,
        second_customer_id,
        third_customer_id,
    ):
        response = client.post(
            f"/api/trips/{source_trip_id}/customers",
            json={"customer_id": customer_id},
        )
        assert response.status_code == 201, response.text

    # Destination already has the first customer.
    response = client.post(
        f"/api/trips/{destination_trip_id}/customers",
        json={"customer_id": first_customer_id},
    )
    assert response.status_code == 201, response.text

    response = client.post(
        f"/api/trips/{destination_trip_id}/customers/"
        f"copy-from/{source_trip_id}"
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert [item["customer_id"] for item in data] == [
        first_customer_id,
        second_customer_id,
        third_customer_id,
    ]

    # Repeating the operation must not create duplicates.
    response = client.post(
        f"/api/trips/{destination_trip_id}/customers/"
        f"copy-from/{source_trip_id}"
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 3


def test_copy_customers_skips_inactive_customers(
    client: TestClient,
) -> None:
    source_trip_id = create_trip(client)
    destination_trip_id = create_trip(client)


    active_customer_id = create_customer(client)
    inactive_customer_id = create_customer(client)

    for customer_id in (active_customer_id, inactive_customer_id):
        response = client.post(
            f"/api/trips/{source_trip_id}/customers",
            json={"customer_id": customer_id},
        )
        assert response.status_code == 201, response.text

    response = client.post(
        f"/api/customers/{inactive_customer_id}/deactivate"
    )
    assert response.status_code in (200, 204), response.text


def test_copy_customers_rejects_same_trip(
    client: TestClient,
) -> None:
    trip_id = create_trip(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers/copy-from/{trip_id}"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Source and destination trips must be different."
    )


def test_copy_customers_rejects_missing_trip(
    client: TestClient,
) -> None:
    existing_trip_id = create_trip(client)

    response = client.post(
        f"/api/trips/{existing_trip_id}/customers/copy-from/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_copy_customers_does_not_copy_quantities(
    client: TestClient,
) -> None:
    source_trip_id = create_trip(client)
    destination_trip_id = create_trip(client)
    customer_id = create_customer(client)

    response = client.post(
        f"/api/trips/{source_trip_id}/customers",
        json={"customer_id": customer_id},
    )
    assert response.status_code == 201, response.text

    fish_type_response = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    )
    assert fish_type_response.status_code == 201, fish_type_response.text
    fish_type_id = fish_type_response.json()["id"]

    response = client.post(
        f"/api/trips/{source_trip_id}/customers/{customer_id}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 100},
    )
    assert response.status_code == 201, response.text

    response = client.post(
        f"/api/trips/{destination_trip_id}/customers/"
        f"copy-from/{source_trip_id}"
    )
    assert response.status_code == 200, response.text

    response = client.get(
        f"/api/trips/{destination_trip_id}/customers/{customer_id}/requirements"
    )
    assert response.status_code == 200, response.text
    assert response.json() == []
