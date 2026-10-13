
from fastapi.testclient import TestClient


def create_supplier(client: TestClient) -> int:
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Requirement Supplier",
            "phone": "9811111101",
            "address": "Pune",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_customer(client: TestClient) -> int:
    response = client.post(
        "/api/customers/",
        json={
            "name": "Requirement Customer",
            "phone": "9811111102",
            "address": "Pune",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_trip(client: TestClient) -> int:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-14",
            "supplier_id": supplier_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def assign_customer(
    client: TestClient,
    trip_id: int,
    customer_id: int,
) -> None:
    response = client.post(
        f"/api/trips/{trip_id}/customers",
        json={"customer_id": customer_id},
    )
    assert response.status_code in (200, 201)


def create_fish_type(client: TestClient, name: str = "Rohu") -> int:
    response = client.post(
        "/api/fish-types/",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_requirement(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)
    fish_type_id = create_fish_type(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={
            "fish_type_id": fish_type_id,
            "quantity_bags": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["trip_customer_id"] > 0
    assert body["fish_type_id"] == fish_type_id
    assert body["quantity_bags"] == 5
    assert body["id"] > 0
    assert "created_at" in body


def test_list_requirements(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)

    rohu_id = create_fish_type(client, "Rohu")
    catla_id = create_fish_type(client, "Catla")

    for fish_type_id, quantity in ((rohu_id, 5), (catla_id, 3)):
        response = client.post(
            f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
            json={
                "fish_type_id": fish_type_id,
                "quantity_bags": quantity,
            },
        )
        assert response.status_code == 201

    response = client.get(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["fish_type_id"] for item in body} == {rohu_id, catla_id}
    assert {item["quantity_bags"] for item in body} == {5, 3}


def test_update_requirement_quantity(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)
    fish_type_id = create_fish_type(client)

    create_response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 5},
    )
    assert create_response.status_code == 201
    requirement_id = create_response.json()["id"]

    response = client.patch(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements/{requirement_id}",
        json={"quantity_bags": 8},
    )

    assert response.status_code == 200
    assert response.json()["quantity_bags"] == 8
    assert response.json()["fish_type_id"] == fish_type_id


def test_duplicate_fish_type_requirement_returns_409(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)
    fish_type_id = create_fish_type(client)

    url = (
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements"
    )
    payload = {"fish_type_id": fish_type_id, "quantity_bags": 5}

    first_response = client.post(url, json=payload)
    assert first_response.status_code == 201

    second_response = client.post(url, json=payload)
    assert second_response.status_code == 409


def test_requirement_rejects_nonpositive_quantity(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)
    fish_type_id = create_fish_type(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 0},
    )

    assert response.status_code == 422


def test_requirement_requires_customer_assignment(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    fish_type_id = create_fish_type(client)

    response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 5},
    )

    assert response.status_code == 404


def test_requirement_rejects_inactive_fish_type(client: TestClient):
    trip_id = create_trip(client)
    customer_id = create_customer(client)
    assign_customer(client, trip_id, customer_id)
    fish_type_id = create_fish_type(client)

    deactivate_response = client.post(
        f"/api/fish-types/{fish_type_id}/deactivate"
    )
    assert deactivate_response.status_code == 200

    response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 5},
    )

    assert response.status_code == 400


def test_update_requirement_rejects_another_customer_requirement(
    client: TestClient,
):
    trip_id = create_trip(client)
    customer_a = create_customer(client)
    customer_b_response = client.post(
        "/api/customers/",
        json={
            "name": "Second Requirement Customer",
            "phone": "9811111103",
            "address": "Pune",
        },
    )
    assert customer_b_response.status_code == 201
    customer_b = customer_b_response.json()["id"]

    assign_customer(client, trip_id, customer_a)
    assign_customer(client, trip_id, customer_b)
    fish_type_id = create_fish_type(client)

    create_response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_a}/requirements",
        json={"fish_type_id": fish_type_id, "quantity_bags": 5},
    )
    assert create_response.status_code == 201
    requirement_id = create_response.json()["id"]

    response = client.patch(
        f"/api/trips/{trip_id}/customers/{customer_b}/requirements/{requirement_id}",
        json={"quantity_bags": 9},
    )

    assert response.status_code == 404
