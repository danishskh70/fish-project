import pytest
from fastapi.testclient import TestClient

from app.models.trip import Trip
from app.models.trip_customer import TripCustomer

# ---------- helpers ----------

def create_fish_type(client: TestClient, name: str) -> int:
    response = client.post("/api/fish-types/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_supplier(client: TestClient) -> int:
    response = client.post(
        "/api/suppliers/",
        json={"name": "Handover Supplier", "phone": "9890000003", "address": "Pune"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_customer(client: TestClient, name: str) -> int:
    # ADJUST payload if your customer create needs other fields.
    response = client.post(
        "/api/customers/",
        json={"name": name, "phone": "9000000001", "address": "Loni"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_trip(client: TestClient, fish_type_ids: list[int]) -> int:
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-16",
            "supplier_id": create_supplier(client),
            "fish_type_ids": fish_type_ids,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_trip_customer(session_factory, trip_id: int, customer_id: int) -> int:
    with session_factory() as db:
        trip_customer = TripCustomer(trip_id=trip_id, customer_id=customer_id)
        db.add(trip_customer)
        db.commit()
        return trip_customer.id


def record_slip(client: TestClient, trip_id: int, items: list[dict]) -> dict:
    response = client.post(
        f"/api/trips/{trip_id}/supplier-deliveries",
        json={"items": items},
    )
    assert response.status_code == 201, response.text
    return response.json()


def post_handover(
    client: TestClient,
    trip_id: int,
    trip_customer_id: int,
    reference: str,
    lines: list[dict],
    **extra,
):
    return client.post(
        f"/api/trips/{trip_id}/handovers",
        json={
            "trip_customer_id": trip_customer_id,
            "submit_reference": reference,
            "lines": lines,
            **extra,
        },
    )


@pytest.fixture
def setup(client: TestClient, test_session_local):
    rohu = create_fish_type(client, "Handover Rohu")
    catla = create_fish_type(client, "Handover Catla")
    mrigal = create_fish_type(client, "Handover Mrigal")
    trip_id = create_trip(client, [rohu, catla, mrigal])
    ravi_id = create_customer(client, "Ravi")
    sunil_id = create_customer(client, "Sunil")
    return {
        "rohu": rohu,
        "catla": catla,
        "mrigal": mrigal,
        "trip_id": trip_id,
        "ravi_tc": add_trip_customer(test_session_local, trip_id, ravi_id),
        "sunil_tc": add_trip_customer(test_session_local, trip_id, sunil_id),
    }


def stock_by_fish(client: TestClient, trip_id: int) -> dict[int, dict]:
    response = client.get(f"/api/trips/{trip_id}/stock")
    assert response.status_code == 200, response.text
    return {row["fish_type_id"]: row for row in response.json()}


# ---------- create ----------

def test_handover_with_multiple_fish_lines(client, setup) -> None:
    response = post_handover(
        client,
        setup["trip_id"],
        setup["ravi_tc"],
        "ref-1",
        [
            {"fish_type_id": setup["rohu"], "bags": 8},
            {"fish_type_id": setup["catla"], "bags": 5},
        ],
        note="first lot",
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trip_id"] == setup["trip_id"]
    assert body["trip_customer_id"] == setup["ravi_tc"]
    assert body["submit_reference"] == "ref-1"
    assert body["total_bags"] == 13
    assert {line["fish_type_id"]: line["bags"] for line in body["lines"]} == {
        setup["rohu"]: 8,
        setup["catla"]: 5,
    }
    assert body["lines"][0]["fish_type_name"]


def test_two_handovers_same_customer_same_trip(client, setup) -> None:
    first = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [{"fish_type_id": setup["rohu"], "bags": 8}],
    )
    second = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-b",
        [{"fish_type_id": setup["rohu"], "bags": 2}],
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    listed = client.get(f"/api/trips/{setup['trip_id']}/handovers")
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_customer_totals_sum_handovers(client, setup) -> None:
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [
            {"fish_type_id": setup["rohu"], "bags": 8},
            {"fish_type_id": setup["catla"], "bags": 5},
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-b",
        [{"fish_type_id": setup["rohu"], "bags": 2}],
    )

    response = client.get(f"/api/trips/{setup['trip_id']}/handover-totals")
    assert response.status_code == 200, response.text
    totals = {
        (row["trip_customer_id"], row["fish_type_id"]): row["bags"]
        for row in response.json()
    }
    assert totals == {
        (setup["ravi_tc"], setup["rohu"]): 10,
        (setup["ravi_tc"], setup["catla"]): 5,
    }


def test_zero_bag_line_allowed(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-zero",
        [{"fish_type_id": setup["rohu"], "bags": 0}],
    )
    assert response.status_code == 201, response.text


def test_get_one_handover_scoped_to_trip(client, setup) -> None:
    created = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 3}],
    ).json()

    ok = client.get(f"/api/trips/{setup['trip_id']}/handovers/{created['id']}")
    assert ok.status_code == 200
    assert ok.json()["id"] == created["id"]

    other_trip = create_trip(client, [setup["rohu"]])
    wrong = client.get(f"/api/trips/{other_trip}/handovers/{created['id']}")
    assert wrong.status_code == 404


# ---------- requirements untouched ----------

def test_requirements_unchanged_after_handover(
    client, setup, test_session_local
) -> None:
    # ADJUST field names if your requirement model differs.
    from app.models.trip_customer_requirement import TripCustomerRequirement

    with test_session_local() as db:
        requirement = TripCustomerRequirement(
            trip_customer_id=setup["ravi_tc"],
            fish_type_id=setup["rohu"],
            quantity_bags=10,
        )
        db.add(requirement)
        db.commit()
        requirement_id = requirement.id

    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 8}],
    )
    assert response.status_code == 201

    with test_session_local() as db:
        row = db.get(TripCustomerRequirement, requirement_id)
        assert row.quantity_bags == 10


# ---------- validation ----------

@pytest.mark.parametrize(
    "bags",
    [-1, -100],
)
def test_negative_bags_rejected(client, setup, bags) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-neg",
        [{"fish_type_id": setup["rohu"], "bags": bags}],
    )
    assert response.status_code == 422


def test_empty_lines_rejected(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-empty", []
    )
    assert response.status_code == 422


def test_duplicate_fish_in_one_submit_rejected(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-dup",
        [
            {"fish_type_id": setup["rohu"], "bags": 1},
            {"fish_type_id": setup["rohu"], "bags": 2},
        ],
    )
    assert response.status_code == 422


def test_blank_reference_rejected(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "   ",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    assert response.status_code == 422


# ---------- not found / wrong trip ----------

def test_unknown_trip_404(client, setup) -> None:
    response = post_handover(
        client, 99999, setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    assert response.status_code == 404


def test_unknown_trip_customer_404(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], 99999, "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    assert response.status_code == 404


def test_trip_customer_from_other_trip_404(
    client, setup, test_session_local
) -> None:
    other_trip = create_trip(client, [setup["rohu"]])
    other_customer = create_customer(client, "Other Trip Customer")
    other_tc = add_trip_customer(test_session_local, other_trip, other_customer)

    response = post_handover(
        client, setup["trip_id"], other_tc, "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    assert response.status_code == 404


def test_unknown_fish_type_404_and_nothing_saved(client, setup) -> None:
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [
            {"fish_type_id": setup["rohu"], "bags": 1},
            {"fish_type_id": 99999, "bags": 1},
        ],
    )
    assert response.status_code == 404

    listed = client.get(f"/api/trips/{setup['trip_id']}/handovers")
    assert listed.json() == []


def test_closed_trip_blocks_handover(client, setup, test_session_local) -> None:
    with test_session_local() as db:
        trip = db.get(Trip, setup["trip_id"])
        trip.status = "CLOSED"
        db.commit()

    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    assert response.status_code == 409


# ---------- stock ----------

def test_stock_left_is_slip_minus_handovers(client, setup) -> None:
    record_slip(
        client,
        setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "delivered_bags": 100},
            {"fish_type_id": setup["catla"], "delivered_bags": 50},
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [
            {"fish_type_id": setup["rohu"], "bags": 8},
            {"fish_type_id": setup["catla"], "bags": 5},
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-b",
        [{"fish_type_id": setup["rohu"], "bags": 2}],
    )

    stock = stock_by_fish(client, setup["trip_id"])
    assert stock[setup["rohu"]]["slip_bags"] == 100
    assert stock[setup["rohu"]]["handed_bags"] == 10
    assert stock[setup["rohu"]]["left_bags"] == 90
    assert stock[setup["catla"]]["left_bags"] == 45
    assert stock[setup["rohu"]]["over_slip"] is False


def test_rejected_and_damaged_do_not_reduce_stock(client, setup) -> None:
    record_slip(
        client,
        setup["trip_id"],
        [
            {
                "fish_type_id": setup["rohu"],
                "delivered_bags": 100,
                "rejected_bags": 5,
                "damaged_bags": 2,
            }
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [{"fish_type_id": setup["rohu"], "bags": 90}],
    )

    row = stock_by_fish(client, setup["trip_id"])[setup["rohu"]]
    assert row["slip_bags"] == 100
    assert row["left_bags"] == 10  # not 3
    assert row["rejected_bags"] == 5
    assert row["damaged_bags"] == 2


def test_two_slips_sum_into_stock(client, setup) -> None:
    record_slip(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "delivered_bags": 60}],
    )
    record_slip(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "delivered_bags": 40}],
    )

    row = stock_by_fish(client, setup["trip_id"])[setup["rohu"]]
    assert row["slip_bags"] == 100


def test_handover_over_slip_allowed_and_flagged(client, setup) -> None:
    record_slip(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "delivered_bags": 10}],
    )
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [{"fish_type_id": setup["rohu"], "bags": 12}],
    )
    assert response.status_code == 201

    row = stock_by_fish(client, setup["trip_id"])[setup["rohu"]]
    assert row["left_bags"] == -2
    assert row["over_slip"] is True


def test_fish_absent_from_slip_allowed_and_flagged(client, setup) -> None:
    record_slip(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "delivered_bags": 100}],
    )
    response = post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-walkin",
        [{"fish_type_id": setup["mrigal"], "bags": 3}],
    )
    assert response.status_code == 201

    row = stock_by_fish(client, setup["trip_id"])[setup["mrigal"]]
    assert row["on_slip"] is False
    assert row["slip_bags"] == 0
    assert row["handed_bags"] == 3
    assert row["left_bags"] == -3
    assert row["over_slip"] is True


def test_stock_without_any_slip(client, setup) -> None:
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-a",
        [{"fish_type_id": setup["rohu"], "bags": 4}],
    )
    row = stock_by_fish(client, setup["trip_id"])[setup["rohu"]]
    assert row["slip_bags"] == 0
    assert row["left_bags"] == -4


def test_stock_unknown_trip_404(client) -> None:
    assert client.get("/api/trips/99999/stock").status_code == 404


# ---------- idempotency ----------

def test_retry_same_reference_returns_same_handover(client, setup) -> None:
    lines = [{"fish_type_id": setup["rohu"], "bags": 8}]
    first = post_handover(client, setup["trip_id"], setup["ravi_tc"], "ref-1", lines)
    retry = post_handover(client, setup["trip_id"], setup["ravi_tc"], "ref-1", lines)

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]

    listed = client.get(f"/api/trips/{setup['trip_id']}/handovers")
    assert len(listed.json()) == 1


def test_same_reference_different_lines_conflict(client, setup) -> None:
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 8}],
    )
    response = post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 9}],
    )
    assert response.status_code == 409


def test_same_reference_different_customer_conflict(client, setup) -> None:
    lines = [{"fish_type_id": setup["rohu"], "bags": 8}]
    post_handover(client, setup["trip_id"], setup["ravi_tc"], "ref-1", lines)
    response = post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-1", lines
    )
    assert response.status_code == 409


# ---------- rollback ----------

def test_failure_after_insert_leaves_nothing(
    client, setup, monkeypatch
) -> None:
    class Boom(Exception):
        pass

    def explode(*args, **kwargs):
        raise Boom("forced failure after flush")

    monkeypatch.setattr("app.services.handover._build_handover_read", explode)

    with pytest.raises(Boom):
        post_handover(
            client, setup["trip_id"], setup["ravi_tc"], "ref-boom",
            [
                {"fish_type_id": setup["rohu"], "bags": 8},
                {"fish_type_id": setup["catla"], "bags": 5},
            ],
        )

    monkeypatch.undo()

    listed = client.get(f"/api/trips/{setup['trip_id']}/handovers")
    assert listed.json() == []
    stock = stock_by_fish(client, setup["trip_id"])
    assert stock == {}