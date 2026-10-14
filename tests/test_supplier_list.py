
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier_list import SupplierList
from app.models.supplier_list_item import SupplierListItem
from app.schemas.supplier_list_item_update import SupplierListItemUpdate
from app.services.supplier_list import (
    finalize_supplier_list,
    generate_supplier_list_draft,
    update_supplier_list_item,
)
from app.services.supplier_list_errors import (
    SupplierListAlreadyFinalError,
    SupplierListItemNotFoundError,
    SupplierListNotEditableError,
    SupplierListNotFoundError,
)
from app.services.trip_requirements_table import (
    TripRequirementsTableNotFoundError,
)


def create_fish_type(client: TestClient, name: str) -> int:
    response = client.post("/api/fish-types/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_trip(client: TestClient, fish_type_ids: list[int]) -> int:
    supplier_response = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier List Test Supplier",
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


def test_generates_draft_with_planned_quantities_and_tub_counts(
    client: TestClient,
    db_session: Session,
) -> None:
    rohu_id = create_fish_type(client, "Supplier List Rohu")
    catla_id = create_fish_type(client, "Supplier List Catla")
    carp_id = create_fish_type(client, "Supplier List Carp")
    trip_id = create_trip(client, [rohu_id, catla_id, carp_id])

    response = client.patch(
        f"/api/trips/{trip_id}/fish-types/{rohu_id}/planned-quantity",
        json={"planned_quantity_bags": 5},
    )
    assert response.status_code == 200, response.text

    response = client.patch(
        f"/api/trips/{trip_id}/fish-types/{catla_id}/planned-quantity",
        json={"planned_quantity_bags": 0},
    )
    assert response.status_code == 200, response.text

    # Carp has no manual override and no demand, so its effective plan is 0.
    result = generate_supplier_list_draft(db_session, trip_id)

    assert result.status == "DRAFT"
    assert result.trip_id == trip_id
    assert result.version_number == 1
    assert result.total_bags == 5
    assert result.total_tubs == 2

    items = {item.fish_type_id: item for item in result.items}

    assert items[rohu_id].quantity_bags == 5
    assert items[rohu_id].tub_count == 2
    assert items[rohu_id].fish_type_name == "Supplier List Rohu"

    assert items[catla_id].quantity_bags == 0
    assert items[catla_id].tub_count == 0

    assert items[carp_id].quantity_bags == 0
    assert items[carp_id].tub_count == 0

    saved_list = db_session.get(SupplierList, result.id)
    assert saved_list is not None

    saved_items = db_session.scalars(
        select(SupplierListItem).where(
            SupplierListItem.supplier_list_id == result.id,
        )
    ).all()
    assert len(saved_items) == 3


def test_generates_sequential_draft_versions(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Supplier List Version Fish")
    trip_id = create_trip(client, [fish_type_id])

    first = generate_supplier_list_draft(db_session, trip_id)
    second = generate_supplier_list_draft(db_session, trip_id)

    assert first.version_number == 1
    assert second.version_number == 2
    assert first.status == "DRAFT"
    assert second.status == "DRAFT"


def test_generating_draft_for_missing_trip_raises_error(
    db_session: Session,
) -> None:
    try:
        generate_supplier_list_draft(db_session, 999999)
    except TripRequirementsTableNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing-trip error")

    assert db_session.scalars(select(SupplierList)).all() == []


def test_updating_bags_recalculates_tubs(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Update Bags Fish")
    trip_id = create_trip(client, [fish_type_id])
    draft = generate_supplier_list_draft(db_session, trip_id)

    result = update_supplier_list_item(
        db_session,
        trip_id,
        draft.id,
        fish_type_id,
        SupplierListItemUpdate(quantity_bags=9),
    )

    item = result.items[0]
    assert item.quantity_bags == 9
    assert item.tub_count == 3
    assert result.total_bags == 9
    assert result.total_tubs == 3


def test_updating_tubs_preserves_bags(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Update Tubs Fish")
    trip_id = create_trip(client, [fish_type_id])
    draft = generate_supplier_list_draft(db_session, trip_id)

    update_supplier_list_item(
        db_session,
        trip_id,
        draft.id,
        fish_type_id,
        SupplierListItemUpdate(quantity_bags=5),
    )

    result = update_supplier_list_item(
        db_session,
        trip_id,
        draft.id,
        fish_type_id,
        SupplierListItemUpdate(tub_count=3),
    )

    assert result.items[0].quantity_bags == 5
    assert result.items[0].tub_count == 3


def test_bag_quantity_takes_precedence_when_both_fields_are_updated(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Both Fields Fish")
    trip_id = create_trip(client, [fish_type_id])
    draft = generate_supplier_list_draft(db_session, trip_id)

    result = update_supplier_list_item(
        db_session,
        trip_id,
        draft.id,
        fish_type_id,
        SupplierListItemUpdate(quantity_bags=5, tub_count=9),
    )

    assert result.items[0].quantity_bags == 5
    assert result.items[0].tub_count == 2


def test_cannot_edit_finalized_supplier_list(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Finalized List Fish")
    trip_id = create_trip(client, [fish_type_id])
    draft = generate_supplier_list_draft(db_session, trip_id)

    saved_list = db_session.get(SupplierList, draft.id)
    assert saved_list is not None
    saved_list.status = "FINAL"
    db_session.commit()

    try:
        update_supplier_list_item(
            db_session,
            trip_id,
            draft.id,
            fish_type_id,
            SupplierListItemUpdate(quantity_bags=5),
        )
    except SupplierListNotEditableError:
        pass
    else:
        raise AssertionError("Expected finalized-list edit to be rejected")


def test_updating_missing_supplier_list_raises_error(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Missing List Fish")
    trip_id = create_trip(client, [fish_type_id])

    try:
        update_supplier_list_item(
            db_session,
            trip_id,
            999999,
            fish_type_id,
            SupplierListItemUpdate(quantity_bags=5),
        )
    except SupplierListNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing-list error")


def test_updating_missing_fish_item_raises_error(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "Existing List Fish")
    trip_id = create_trip(client, [fish_type_id])
    draft = generate_supplier_list_draft(db_session, trip_id)

    try:
        update_supplier_list_item(
            db_session,
            trip_id,
            draft.id,
            999999,
            SupplierListItemUpdate(quantity_bags=5),
        )
    except SupplierListItemNotFoundError:
        pass
    else:
        raise AssertionError("Expected missing-item error")
def test_update_supplier_list_item_endpoint_recalculates_tubs(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "API Update Bags Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert draft_response.status_code == 201, draft_response.text
    draft = draft_response.json()

    response = client.patch(
        f"/api/trips/{trip_id}/supplier-lists/{draft['id']}"
        f"/items/{fish_type_id}",
        json={"quantity_bags": 9},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["items"][0]["quantity_bags"] == 9
    assert data["items"][0]["tub_count"] == 3
    assert data["total_bags"] == 9
    assert data["total_tubs"] == 3



def test_update_supplier_list_item_endpoint_rejects_finalized_list(
    client: TestClient,
    db_session: Session,
) -> None:
    fish_type_id = create_fish_type(client, "API Finalized Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert draft_response.status_code == 201, draft_response.text
    draft_id = draft_response.json()["id"]

    saved_list = db_session.get(SupplierList, draft_id)
    assert saved_list is not None
    saved_list.status = "FINAL"
    db_session.commit()

    response = client.patch(
        f"/api/trips/{trip_id}/supplier-lists/{draft_id}"
        f"/items/{fish_type_id}",
        json={"quantity_bags": 9},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only draft supplier lists can be edited."
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"quantity_bags": -1},
        {},
        {"quantity_bags": None},
        {"unexpected_field": 5},
    ],
)
def test_update_supplier_list_item_rejects_invalid_payloads(
    client: TestClient,
    payload: dict,
) -> None:
    fish_type_id = create_fish_type(client, "Validation Test Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert draft_response.status_code == 201, draft_response.text
    draft_id = draft_response.json()["id"]

    response = client.patch(
        f"/api/trips/{trip_id}/supplier-lists/{draft_id}"
        f"/items/{fish_type_id}",
        json=payload,
    )

    assert response.status_code == 422, response.text

def test_finalize_draft_supplier_list(db_session, client: TestClient) -> None:
    fish_type_id = create_fish_type(client, "Finalize Test Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft = generate_supplier_list_draft(db_session, trip_id)

    finalized = finalize_supplier_list(
        db_session,
        trip_id,
        draft.id,
    )

    assert finalized.status == "FINAL"
    assert finalized.finalized_at is not None
    assert finalized.id == draft.id
    assert finalized.items == draft.items


def test_cannot_finalize_supplier_list_twice(
    db_session,
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Finalize Twice Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft = generate_supplier_list_draft(db_session, trip_id)
    finalize_supplier_list(db_session, trip_id, draft.id)

    with pytest.raises(SupplierListNotEditableError):
        finalize_supplier_list(db_session, trip_id, draft.id)


def test_cannot_finalize_when_another_list_is_final(
    db_session,
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Existing Final Fish")
    trip_id = create_trip(client, [fish_type_id])

    first_draft = generate_supplier_list_draft(db_session, trip_id)
    finalize_supplier_list(db_session, trip_id, first_draft.id)

    second_draft = generate_supplier_list_draft(db_session, trip_id)

    with pytest.raises(SupplierListAlreadyFinalError):
        finalize_supplier_list(db_session, trip_id, second_draft.id)


def test_finalize_missing_supplier_list_raises_error(
    db_session,
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Missing Final Fish")
    trip_id = create_trip(client, [fish_type_id])

    with pytest.raises(SupplierListNotFoundError):
        finalize_supplier_list(
            db_session,
            trip_id,
            supplier_list_id=999999,
        )


def test_list_supplier_lists_endpoint_returns_versions_newest_first(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "List History Fish")
    trip_id = create_trip(client, [fish_type_id])

    first_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert second_response.status_code == 201, second_response.text

    response = client.get(
        f"/api/trips/{trip_id}/supplier-lists"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data) == 2
    assert [item["version_number"] for item in data] == [2, 1]
    assert [item["id"] for item in data] == [
        second_response.json()["id"],
        first_response.json()["id"],
    ]


def test_list_supplier_lists_endpoint_returns_empty_list(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Empty History Fish")
    trip_id = create_trip(client, [fish_type_id])

    response = client.get(
        f"/api/trips/{trip_id}/supplier-lists"
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_get_supplier_list_endpoint_returns_items_and_totals(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "List Detail Fish")
    trip_id = create_trip(client, [fish_type_id])

    draft_response = client.post(
        f"/api/trips/{trip_id}/supplier-lists/drafts"
    )
    assert draft_response.status_code == 201, draft_response.text
    draft = draft_response.json()

    update_response = client.patch(
        f"/api/trips/{trip_id}/supplier-lists/{draft['id']}"
        f"/items/{fish_type_id}",
        json={"quantity_bags": 9},
    )
    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/api/trips/{trip_id}/supplier-lists/{draft['id']}"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == draft["id"]
    assert data["trip_id"] == trip_id
    assert data["version_number"] == 1
    assert data["status"] == "DRAFT"
    assert data["total_bags"] == 9
    assert data["total_tubs"] == 3
    assert len(data["items"]) == 1
    assert data["items"][0]["fish_type_id"] == fish_type_id
    assert data["items"][0]["quantity_bags"] == 9
    assert data["items"][0]["tub_count"] == 3


def test_list_supplier_lists_endpoint_returns_404_for_missing_trip(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/trips/999999/supplier-lists"
    )

    assert response.status_code == 404


def test_get_supplier_list_endpoint_returns_404_for_missing_list(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Missing Detail Fish")
    trip_id = create_trip(client, [fish_type_id])

    response = client.get(
        f"/api/trips/{trip_id}/supplier-lists/999999"
    )

    assert response.status_code == 404


def test_get_supplier_list_endpoint_returns_404_for_wrong_trip(
    client: TestClient,
) -> None:
    fish_type_id = create_fish_type(client, "Wrong Trip Fish")
    first_trip_id = create_trip(client, [fish_type_id])
    second_trip_id = create_trip(client, [fish_type_id])

    draft_response = client.post(
        f"/api/trips/{first_trip_id}/supplier-lists/drafts"
    )
    assert draft_response.status_code == 201, draft_response.text
    draft_id = draft_response.json()["id"]

    response = client.get(
        f"/api/trips/{second_trip_id}/supplier-lists/{draft_id}"
    )

    assert response.status_code == 404
