
from fastapi.testclient import TestClient


def update_requirement_quantity(
    client: TestClient,
    trip_id: int,
    customer_id: int,
    requirement_id: int,
    quantity_bags: int,
) -> None:
    response = client.patch(
        f"/api/trips/{trip_id}/customers/{customer_id}/"
        f"requirements/{requirement_id}",
        json={"quantity_bags": quantity_bags},
    )
    assert response.status_code == 200, response.text

def create_fish_type(client: TestClient, name: str) -> int:
    response = client.post(
        "/api/fish-types/",
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_customer(
    client: TestClient,
    name: str,
    phone: str,
) -> int:
    response = client.post(
        "/api/customers/",
        json={
            "name": name,
            "phone": phone,
            "address": "Pune",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_trip(
    client: TestClient,
    fish_type_ids: list[int],
) -> int:
    supplier_response = client.post(
        "/api/suppliers/",
        json={
            "name": "Requirements Table Supplier",
            "phone": "9890000001",
            "address": "Pune",
        },
    )
    assert supplier_response.status_code == 201, supplier_response.text

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-13",
            "supplier_id": supplier_response.json()["id"],
            "fish_type_ids": fish_type_ids,
        },
    )
    assert response.status_code == 201, response.text
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
    assert response.status_code == 201, response.text


def save_requirement(
    client: TestClient,
    trip_id: int,
    customer_id: int,
    fish_type_id: int,
    quantity_bags: int,
) -> None:
    response = client.post(
        f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
        json={
            "fish_type_id": fish_type_id,
            "quantity_bags": quantity_bags,
        },
    )
    assert response.status_code == 201, response.text


def test_requirements_table_calculates_quantities_and_totals(
    client: TestClient,
) -> None:
    rohu_id = create_fish_type(client, "Table Test Rohu")
    catla_id = create_fish_type(client, "Table Test Catla")
    trip_id = create_trip(client, [rohu_id, catla_id])

    customer_a = create_customer(
        client,
        "Table Customer A",
        "9890000002",
    )
    customer_b = create_customer(
        client,
        "Table Customer B",
        "9890000003",
    )

    assign_customer(client, trip_id, customer_a)
    assign_customer(client, trip_id, customer_b)

    save_requirement(
        client, trip_id, customer_a, rohu_id, 5
    )
    save_requirement(
        client, trip_id, customer_a, catla_id, 3
    )
    save_requirement(
        client, trip_id, customer_b, rohu_id, 2
    )

    response = client.get(
        f"/api/trips/{trip_id}/requirements-table"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["trip_id"] == trip_id
    assert {
        fish["id"]: fish["name"]
        for fish in data["fish_types"]
    } == {
        rohu_id: "Table Test Rohu",
        catla_id: "Table Test Catla",
    }

    customers = {
        customer["customer_id"]: customer
        for customer in data["customers"]
    }

    customer_a_data = customers[customer_a]
    customer_b_data = customers[customer_b]

    assert customer_a_data["name"] == "Table Customer A"
    assert customer_a_data["phone"] == "9890000002"
    assert customer_a_data["address"] == "Pune"
    assert customer_a_data["total_bags"] == 8

    assert {
        item["fish_type_id"]: item["quantity_bags"]
        for item in customer_a_data["quantities"]
    } == {
        rohu_id: 5,
        catla_id: 3,
    }

    assert customer_b_data["total_bags"] == 2
    assert {
        item["fish_type_id"]: item["quantity_bags"]
        for item in customer_b_data["quantities"]
    } == {
        rohu_id: 2,
        catla_id: 0,
    }

    assert {
        item["fish_type_id"]: item["quantity_bags"]
        for item in data["fish_totals"]
    } == {
        rohu_id: 7,
        catla_id: 3,
    }

    assert data["grand_total_bags"] == 10


def test_requirements_table_returns_404_for_missing_trip(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/trips/999999/requirements-table"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


def test_requirements_table_calculates_planned_quantities_and_shortfalls(
    client: TestClient,
) -> None:
    fish_type_ids = [
        create_fish_type(client, f"Planning Test Fish {i}")
        for i in range(1, 5)
    ]
    trip_id = create_trip(client, fish_type_ids)

    customer_id = create_customer(
        client,
        "Planning Test Customer",
        "9890000010",
    )
    assign_customer(client, trip_id, customer_id)

    # Each fish type has demand of 30 bags.
    for fish_type_id in fish_type_ids:
        save_requirement(
            client, trip_id, customer_id, fish_type_id, 30
        )

    # Automatic planning: null override.
    # Explicit zero, under-planning, and over-planning.
    overrides = [None, 0, 24, 40]

    for fish_type_id, planned_quantity in zip(
        fish_type_ids, overrides, strict=True
    ):
        response = client.patch(
            f"/api/trips/{trip_id}/fish-types/"
            f"{fish_type_id}/planned-quantity",
            json={"planned_quantity_bags": planned_quantity},
        )
        assert response.status_code == 200, response.text

    response = client.get(
        f"/api/trips/{trip_id}/requirements-table"
    )
    assert response.status_code == 200, response.text

    fish_totals = {
        item["fish_type_id"]: item
        for item in response.json()["fish_totals"]
    }

    expected = [
        (None, 30, 0, False),
        (0, 0, 30, True),
        (24, 24, 6, True),
        (40, 40, 0, False),
    ]

    for fish_type_id, (
        planned,
        effective,
        shortfall,
        has_shortfall,
    ) in zip(fish_type_ids, expected, strict=True):
        result = fish_totals[fish_type_id]

        assert result["quantity_bags"] == 30
        assert result["planned_quantity_bags"] == planned
        assert result["effective_planned_quantity_bags"] == effective
        assert result["shortfall_bags"] == shortfall
        assert result["shortfall_exists"] is has_shortfall


def test_demand_changes_update_automatic_plan_but_preserve_manual_plan(
    client: TestClient,
) -> None:
    fish_type_ids = [
        create_fish_type(client, "Automatic Planning Fish"),
        create_fish_type(client, "Manual Planning Fish"),
    ]
    trip_id = create_trip(client, fish_type_ids)

    customer_id = create_customer(
        client,
        "Demand Change Customer",
        "9890000011",
    )
    assign_customer(client, trip_id, customer_id)

    automatic_fish_id, manual_fish_id = fish_type_ids

    # Create initial requirements and retain their IDs.
    requirement_ids = {}

    for fish_type_id in fish_type_ids:
        response = client.post(
            f"/api/trips/{trip_id}/customers/{customer_id}/requirements",
            json={
                "fish_type_id": fish_type_id,
                "quantity_bags": 30,
            },
        )
        assert response.status_code == 201, response.text
        requirement_ids[fish_type_id] = response.json()["id"]

    # Keep one fish type automatic; fix the other at 24 bags.
    for fish_type_id, planned_quantity in [
        (automatic_fish_id, None),
        (manual_fish_id, 24),
    ]:
        response = client.patch(
            f"/api/trips/{trip_id}/fish-types/"
            f"{fish_type_id}/planned-quantity",
            json={"planned_quantity_bags": planned_quantity},
        )
        assert response.status_code == 200, response.text

    # Change demand from 30 to 40 using the existing update endpoint.
    for fish_type_id in fish_type_ids:
        update_requirement_quantity(
            client,
            trip_id,
            customer_id,
            requirement_ids[fish_type_id],
            40,
        )

    response = client.get(
        f"/api/trips/{trip_id}/requirements-table"
    )
    assert response.status_code == 200, response.text

    fish_totals = {
        item["fish_type_id"]: item
        for item in response.json()["fish_totals"]
    }

    automatic = fish_totals[automatic_fish_id]
    assert automatic["quantity_bags"] == 40
    assert automatic["planned_quantity_bags"] is None
    assert automatic["effective_planned_quantity_bags"] == 40
    assert automatic["shortfall_bags"] == 0
    assert automatic["shortfall_exists"] is False

    manual = fish_totals[manual_fish_id]
    assert manual["quantity_bags"] == 40
    assert manual["planned_quantity_bags"] == 24
    assert manual["effective_planned_quantity_bags"] == 24
    assert manual["shortfall_bags"] == 16
    assert manual["shortfall_exists"] is True
