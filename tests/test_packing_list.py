
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier_list import SupplierList
from app.models.supplier_list_item import SupplierListItem
from app.models.trip_fish_type import TripFishType
from app.schemas.supplier_list_item_update import SupplierListItemUpdate
from app.services.supplier_list import (
    finalize_supplier_list,
    generate_supplier_list_draft,
    update_supplier_list_item,
)


def create_supplier(client: TestClient) -> int:
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Packing Test Supplier",
            "phone": "9876543210",
            "address": "Test Address",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_fish_type(
    client: TestClient,
    name: str,
    *,
    active: bool = True,
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


def create_trip(
    client: TestClient,
    fish_type_ids: list[int],
) -> int:
    supplier_id = create_supplier(client)

    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-14",
            "supplier_id": supplier_id,
            "fish_type_ids": fish_type_ids,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_packing_list(
    client: TestClient,
    trip_id: int,
    fish_type_id: int,
    quantity_bags: int = 10,
) -> dict:
    response = client.post(
        f"/api/trips/{trip_id}/packing-list",
        json={
            "items": [
                {
                    "fish_type_id": fish_type_id,
                    "quantity_bags": quantity_bags,
                }
            ]
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_packing_list(client: TestClient) -> None:
    fish_type_id = create_fish_type(client, "Packing Rohu")
    trip_id = create_trip(client, [fish_type_id])

    created = create_packing_list(
        client,
        trip_id,
        fish_type_id,
        10,
    )

    assert created["trip_id"] == trip_id
    assert created["total_bags"] == 10
    assert len(created["items"]) == 1
    assert created["items"][0]["fish_type_id"] == fish_type_id
    assert created["items"][0]["quantity_bags"] == 10

    response = client.get(
        f"/api/trips/{trip_id}/packing-list"
    )

    assert response.status_code == 200, response.text
    assert response.json() == created


def test_cannot_create_second_packing_list(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Katla")
    trip_id = create_trip(client, [fish_type_id])

    create_packing_list(client, trip_id, fish_type_id)

    response = client.post(
        f"/api/trips/{trip_id}/packing-list",
        json={
            "items": [
                {
                    "fish_type_id": fish_type_id,
                    "quantity_bags": 5,
                }
            ]
        },
    )

    assert response.status_code == 409


def test_add_fish_type_to_existing_packing_list(
    client: TestClient,
    db_session: Session,
) -> None:
    first_id = create_fish_type(client, "Packing Rohu Add")
    second_id = create_fish_type(client, "Packing Catla Add")
    trip_id = create_trip(client, [first_id])

    create_packing_list(client, trip_id, first_id, 10)

    response = client.post(
        f"/api/trips/{trip_id}/packing-list/items",
        json={
            "fish_type_id": second_id,
            "quantity_bags": 3,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total_bags"] == 13
    assert len(data["items"]) == 2
    assert any(
        item["fish_type_id"] == second_id
        and item["quantity_bags"] == 3
        for item in data["items"]
    )

    association = db_session.scalar(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id == second_id,
        )
    )

    assert association is not None
    assert association.planned_quantity_bags is None


def test_cannot_add_duplicate_fish_type(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Duplicate")
    trip_id = create_trip(client, [fish_type_id])
    create_packing_list(client, trip_id, fish_type_id)

    response = client.post(
        f"/api/trips/{trip_id}/packing-list/items",
        json={
            "fish_type_id": fish_type_id,
            "quantity_bags": 2,
        },
    )

    assert response.status_code == 409


def test_update_quantity_and_recalculate_total(
    client: TestClient,
) -> None:
    first_id = create_fish_type(client, "Packing Update One")
    second_id = create_fish_type(client, "Packing Update Two")
    trip_id = create_trip(client, [first_id, second_id])

    create_response = client.post(
        f"/api/trips/{trip_id}/packing-list",
        json={
            "items": [
                {"fish_type_id": first_id, "quantity_bags": 10},
                {"fish_type_id": second_id, "quantity_bags": 5},
            ]
        },
    )
    assert create_response.status_code == 201, create_response.text

    response = client.patch(
        f"/api/trips/{trip_id}/packing-list/items/{first_id}",
        json={"quantity_bags": 12},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_bags"] == 17
    assert next(
        item["quantity_bags"]
        for item in data["items"]
        if item["fish_type_id"] == first_id
    ) == 12


def test_update_quantity_to_zero(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Zero")
    trip_id = create_trip(client, [fish_type_id])
    create_packing_list(client, trip_id, fish_type_id, 5)

    response = client.patch(
        f"/api/trips/{trip_id}/packing-list/items/{fish_type_id}",
        json={"quantity_bags": 0},
    )

    assert response.status_code == 200, response.text
    assert response.json()["total_bags"] == 0
    assert response.json()["items"][0]["quantity_bags"] == 0


def test_cannot_update_quantity_to_negative(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Negative")
    trip_id = create_trip(client, [fish_type_id])
    create_packing_list(client, trip_id, fish_type_id)

    response = client.patch(
        f"/api/trips/{trip_id}/packing-list/items/{fish_type_id}",
        json={"quantity_bags": -1},
    )

    assert response.status_code == 422


def test_remove_item_and_recalculate_total(
    client: TestClient,
) -> None:
    first_id = create_fish_type(client, "Packing Remove One")
    second_id = create_fish_type(client, "Packing Remove Two")
    trip_id = create_trip(client, [first_id, second_id])

    response = client.post(
        f"/api/trips/{trip_id}/packing-list",
        json={
            "items": [
                {"fish_type_id": first_id, "quantity_bags": 10},
                {"fish_type_id": second_id, "quantity_bags": 5},
            ]
        },
    )
    assert response.status_code == 201, response.text

    response = client.delete(
        f"/api/trips/{trip_id}/packing-list/items/{first_id}"
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_bags"] == 5
    assert len(data["items"]) == 1
    assert data["items"][0]["fish_type_id"] == second_id


def test_cannot_remove_last_fish_type(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Last Item")
    trip_id = create_trip(client, [fish_type_id])
    create_packing_list(client, trip_id, fish_type_id)

    response = client.delete(
        f"/api/trips/{trip_id}/packing-list/items/{fish_type_id}"
    )

    assert response.status_code == 409


def test_cannot_add_inactive_fish_type(
    client: TestClient,
) -> None:
    first_id = create_fish_type(client, "Packing Active")
    inactive_id = create_fish_type(
        client,
        "Packing Inactive",
        active=False,
    )
    trip_id = create_trip(client, [first_id])
    create_packing_list(client, trip_id, first_id)

    response = client.post(
        f"/api/trips/{trip_id}/packing-list/items",
        json={
            "fish_type_id": inactive_id,
            "quantity_bags": 1,
        },
    )

    assert response.status_code == 400


def test_packing_list_requires_at_least_one_item(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Packing Empty")
    trip_id = create_trip(client, [fish_type_id])

    response = client.post(
        f"/api/trips/{trip_id}/packing-list",
        json={"items": []},
    )

    assert response.status_code == 422


def test_adding_item_does_not_change_existing_planned_quantity(
    client: TestClient,
    db_session: Session,
) -> None:
    first_id = create_fish_type(client, "Packing Planned One")
    second_id = create_fish_type(client, "Packing Planned Two")
    trip_id = create_trip(client, [first_id, second_id])

    planned = db_session.scalar(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id == first_id,
        )
    )
    assert planned is not None
    planned.planned_quantity_bags = 20
    db_session.commit()

    create_packing_list(client, trip_id, first_id, 10)

    response = client.post(
        f"/api/trips/{trip_id}/packing-list/items",
        json={
            "fish_type_id": second_id,
            "quantity_bags": 3,
        },
    )

    assert response.status_code == 201, response.text

    db_session.expire_all()
    planned_after = db_session.scalar(
        select(TripFishType).where(
            TripFishType.trip_id == trip_id,
            TripFishType.fish_type_id == first_id,
        )
    )

    assert planned_after is not None
    assert planned_after.planned_quantity_bags == 20


def test_packing_list_changes_do_not_modify_finalized_supplier_list(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Boundary Test Fish")
    trip_id = create_trip(client, [fish_type_id])

    # Create a supplier-list draft and set its quantity.
    supplier_list = generate_supplier_list_draft(db_session, trip_id)

    update_supplier_list_item(
        db_session,
        trip_id,
        supplier_list.id,
        fish_type_id,
        SupplierListItemUpdate(quantity_bags=7),
    )

    # Finalize the supplier list before creating the packing list.
    finalized_list = finalize_supplier_list(
        db_session,
        trip_id,
        supplier_list.id,
    )

    assert finalized_list.status == "FINAL"

    # Create and then edit the separate packing list.
    create_packing_list(client, trip_id, fish_type_id, quantity_bags=10)

    response = client.patch(
        f"/api/trips/{trip_id}/packing-list/items/{fish_type_id}",
        json={"quantity_bags": 12},
    )
    assert response.status_code == 200, response.text

    # Reload the supplier-list records and verify they remain unchanged.
    db_session.expire_all()

    saved_list = db_session.get(SupplierList, supplier_list.id)
    assert saved_list is not None
    assert saved_list.status == "FINAL"

    saved_item = db_session.scalar(
        select(SupplierListItem).where(
            SupplierListItem.supplier_list_id == supplier_list.id,
            SupplierListItem.fish_type_id == fish_type_id,
        )
    )

    assert saved_item is not None
    assert saved_item.quantity_bags == 7
    assert saved_item.tub_count == 2
