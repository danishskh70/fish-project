import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.supplier_delivery import SupplierDelivery, SupplierDeliveryItem


def create_fish_type(client: TestClient, name: str) -> int:
    response = client.post("/api/fish-types/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_supplier(client: TestClient) -> int:
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier Delivery Test Supplier",
            "phone": "9890000002",
            "address": "Pune",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_trip(client: TestClient, fish_type_ids: list[int]) -> int:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-15",
            "supplier_id": supplier_id,
            "fish_type_ids": fish_type_ids,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_final_supplier_list(client: TestClient, trip_id: int) -> int:
    response = client.post(f"/api/trips/{trip_id}/supplier-lists/drafts")
    assert response.status_code == 201, response.text
    supplier_list_id = response.json()["id"]

    response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/{supplier_list_id}/finalize"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "FINAL"

    return supplier_list_id


def test_slip_without_supplier_list_records_actual_delivery(
    client: TestClient,
) -> None:
    seed_a_id = create_fish_type(client, "Delivery Rohu")
    seed_b_id = create_fish_type(client, "Delivery Catla")
    trip_id = create_trip(client, [seed_a_id, seed_b_id])

    # A single trip in a fresh database is assigned id 1.
    

    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={
            "items": [
                {"fish_type_id": seed_a_id, "delivered_bags": 10},
                {"fish_type_id": seed_b_id, "delivered_bags": 5},
            ],
            "tub_count": 3,
            "vehicle": "MH12",
            "driver": "Ravi",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["trip_id"] == trip_id
    assert body["supplier_list_id"] is None
    assert body["tub_count"] == 3
    assert body["vehicle"] == "MH12"
    assert body["driver"] == "Ravi"

    # Slip total is derived from the item rows, not stored.
    assert body["total_bags"] == 15

    items_by_fish_type = {item["fish_type_id"]: item for item in body["items"]}
    assert len(items_by_fish_type) == 2

    seed_a_item = items_by_fish_type[seed_a_id]
    assert seed_a_item["delivered_bags"] == 10
    assert seed_a_item["planned_bags"] is None
    assert seed_a_item["accepted_bags"] == 10
    assert seed_a_item["shortage_bags"] is None
    assert seed_a_item["excess_bags"] is None

    seed_b_item = items_by_fish_type[seed_b_id]
    assert seed_b_item["delivered_bags"] == 5
    assert seed_b_item["planned_bags"] is None


def test_multiple_slips_on_one_trip_derive_trip_total(client: TestClient) -> None:
    seed_a_id = create_fish_type(client, "Multi Slip Rohu")
    trip_id = create_trip(client, [seed_a_id])

    first = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_a_id, "delivered_bags": 10}]},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_a_id, "delivered_bags": 2}]},
    )
    assert second.status_code == 201, second.text

    listing = client.get(f"/api/trips/{trip_id}/supplier-deliveries")
    assert listing.status_code == 200, listing.text
    slips = listing.json()
    assert len(slips) == 2

    trip_total_for_a = sum(
        item["delivered_bags"]
        for slip in slips
        for item in slip["items"]
        if item["fish_type_id"] == seed_a_id
    )
    assert trip_total_for_a == 12


def test_supplier_list_from_another_trip_is_rejected(client: TestClient) -> None:
    seed_id = create_fish_type(client, "Cross Trip Rohu")
    trip_one_id = create_trip(client, [seed_id])
    trip_two_id = create_trip(client, [seed_id])

    other_trip_supplier_list_id = create_final_supplier_list(client, trip_two_id)

    response = client.post(
        f"/api/trips/{trip_one_id}/supplier-deliveries",
        json={
            "supplier_list_id": other_trip_supplier_list_id,
            "items": [{"fish_type_id": seed_id, "delivered_bags": 1}],
        },
    )

    assert response.status_code in (400, 409), response.text


def test_nonexistent_trip_returns_404(client: TestClient) -> None:
    seed_id = create_fish_type(client, "Missing Trip Rohu")

    response = client.post(
        "/api/trips/999/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_id, "delivered_bags": 1}]},
    )

    assert response.status_code == 404, response.text


def test_negative_quantity_is_rejected(client: TestClient) -> None:
    seed_id = create_fish_type(client, "Negative Rohu")
    trip_id = create_trip(client, [seed_id])

    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_id, "delivered_bags": -1}]},
    )

    assert response.status_code == 422, response.text


def test_rejected_over_delivered_is_rejected_by_request_and_database(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_id = create_fish_type(client, "Rejected Rohu")
    trip_id = create_trip(client, [seed_id])

    # Request path: the schema validator must reject the inconsistent item.
    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={
            "items": [
                {
                    "fish_type_id": seed_id,
                    "delivered_bags": 3,
                    "rejected_bags": 4,
                }
            ]
        },
    )
    assert response.status_code == 422, response.text

    # Database path: the check constraint must be enforced even when the
    # schema validation layer is bypassed.
    delivery = SupplierDelivery(trip_id=trip_id, supplier_list_id=None)
    db_session.add(delivery)
    db_session.flush()

    db_session.add(
        SupplierDeliveryItem(
            delivery_id=delivery.id,
            fish_type_id=seed_id,
            fish_type_name="Rejected Rohu",
            planned_bags=None,
            delivered_bags=3,
            rejected_bags=4,
            damaged_bags=0,
        )
    )

    try:
        with pytest.raises(IntegrityError):
            db_session.flush()
    finally:
        db_session.rollback()


def test_fish_type_not_on_supplier_list_is_allowed(client: TestClient) -> None:
    listed_seed_id = create_fish_type(client, "Listed Rohu")
    unlisted_seed_id = create_fish_type(client, "Unlisted Catla")
    trip_id = create_trip(client, [listed_seed_id])

    supplier_list_id = create_final_supplier_list(client, trip_id)

    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={
            "supplier_list_id": supplier_list_id,
            "items": [
                {"fish_type_id": listed_seed_id, "delivered_bags": 10},
                {"fish_type_id": unlisted_seed_id, "delivered_bags": 5},
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["supplier_list_id"] == supplier_list_id

    items_by_fish_type = {item["fish_type_id"]: item for item in body["items"]}
    assert len(items_by_fish_type) == 2

    # The listed fish type keeps its planned snapshot.
    listed_item = items_by_fish_type[listed_seed_id]
    assert listed_item["planned_bags"] == 0
    assert listed_item["shortage_bags"] == 0
    assert listed_item["excess_bags"] == 10

    # The unlisted fish type was actually delivered, so it is recorded with
    # no planned quantity.
    unlisted_item = items_by_fish_type[unlisted_seed_id]
    assert unlisted_item["planned_bags"] is None
    assert unlisted_item["shortage_bags"] is None
    assert unlisted_item["excess_bags"] is None
    assert unlisted_item["delivered_bags"] == 5


def test_slip_item_shortage_and_excess_are_none_when_unplanned(
    client: TestClient,
) -> None:
    seed_id = create_fish_type(client, "Unplanned Compute Rohu")
    trip_id = create_trip(client, [seed_id])

    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={
            "items": [
                {"fish_type_id": seed_id, "delivered_bags": 10}
            ]
        },
    )

    assert response.status_code == 201, response.text
    item = response.json()["items"][0]
    assert item["planned_bags"] is None
    assert item["shortage_bags"] is None
    assert item["excess_bags"] is None


def test_duplicate_fish_types_in_request_are_rejected(client: TestClient) -> None:
    seed_id = create_fish_type(client, "Dup Rohu")
    trip_id = create_trip(client, [seed_id])

    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={
            "items": [
                {"fish_type_id": seed_id, "delivered_bags": 1},
                {"fish_type_id": seed_id, "delivered_bags": 2},
            ]
        },
    )

    assert response.status_code == 422, response.text


def test_list_and_get_delivery_are_scoped_to_trip(client: TestClient) -> None:
    seed_id = create_fish_type(client, "Scope Rohu")
    trip_a = create_trip(client, [seed_id])
    trip_b = create_trip(client, [seed_id])

    a1 = client.post(
        f"/api/trips/{trip_a}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_id, "delivered_bags": 5}]},
    )
    assert a1.status_code == 201, a1.text
    a2 = client.post(
        f"/api/trips/{trip_a}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_id, "delivered_bags": 3}]},
    )
    assert a2.status_code == 201, a2.text

    b1 = client.post(
        f"/api/trips/{trip_b}/supplier-deliveries",
        json={"items": [{"fish_type_id": seed_id, "delivered_bags": 7}]},
    )
    assert b1.status_code == 201, b1.text

    list_a = client.get(f"/api/trips/{trip_a}/supplier-deliveries")
    assert list_a.status_code == 200, list_a.text
    assert len(list_a.json()) == 2

    list_b = client.get(f"/api/trips/{trip_b}/supplier-deliveries")
    assert list_b.status_code == 200, list_b.text
    assert len(list_b.json()) == 1

    a1_id = a1.json()["id"]
    assert client.get(f"/api/trips/{trip_a}/supplier-deliveries/{a1_id}").status_code == 200

    b1_id = b1.json()["id"]
    assert client.get(f"/api/trips/{trip_a}/supplier-deliveries/{b1_id}").status_code == 404
