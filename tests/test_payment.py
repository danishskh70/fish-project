from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.trip_fish_type import TripFishType
from tests.test_handover import (
    add_trip_customer,
    close,
    create_customer,
    create_fish_type,
    create_trip,
    post_handover,
    record_slip,
)

# ---------- helpers ----------


def d(value) -> Decimal:
    return Decimal(str(value))


def pay(
    client,
    trip_id,
    trip_customer_id,
    reference,
    amount,
    method="CASH",
    kind="PAYMENT",
    **extra,
):
    return client.post(
        f"/api/trips/{trip_id}/customers/{trip_customer_id}/payments",
        json={
            "reference": reference,
            "amount": amount,
            "method": method,
            "kind": kind,
            **extra,
        },
    )


def set_default_rate(session_factory, trip_id, fish_type_id, rate):
    with session_factory() as db:
        row = db.scalar(
            select(TripFishType).where(
                TripFishType.trip_id == trip_id,
                TripFishType.fish_type_id == fish_type_id,
            )
        )
        assert row is not None, "trip_fish_types row missing. ADJUST helper."
        row.rate_per_bag = Decimal(rate)
        db.commit()


def summary(client, trip_id) -> dict:
    response = client.get(f"/api/trips/{trip_id}/payments-summary")
    assert response.status_code == 200, response.text
    return response.json()


def row_for(body: dict, trip_customer_id: int) -> dict:
    return next(
        c for c in body["customers"] if c["trip_customer_id"] == trip_customer_id
    )


def all_keys(node) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            keys |= all_keys(value)
    elif isinstance(node, list):
        for item in node:
            keys |= all_keys(item)
    return keys


@pytest.fixture
def setup(client, test_session_local):
    rohu = create_fish_type(client, "Pay Rohu")
    catla = create_fish_type(client, "Pay Catla")
    trip_id = create_trip(client, [rohu, catla])
    ravi_id = create_customer(client, "Ravi")
    sunil_id = create_customer(client, "Sunil")
    return {
        "rohu": rohu,
        "catla": catla,
        "trip_id": trip_id,
        "ravi_tc": add_trip_customer(test_session_local, trip_id, ravi_id),
        "sunil_tc": add_trip_customer(test_session_local, trip_id, sunil_id),
    }


@pytest.fixture
def priced(client, setup, test_session_local):
    """Rohu 100, catla 50. Ravi takes 8 rohu + 4 catla. Bill = 1000."""
    set_default_rate(test_session_local, setup["trip_id"], setup["rohu"], "100")
    set_default_rate(test_session_local, setup["trip_id"], setup["catla"], "50")
    response = post_handover(
        client,
        setup["trip_id"],
        setup["ravi_tc"],
        "h-1",
        [
            {"fish_type_id": setup["rohu"], "bags": 8},
            {"fish_type_id": setup["catla"], "bags": 4},
        ],
    )
    assert response.status_code == 201, response.text
    return setup


# ---------- create ----------


def test_create_payment(client, setup) -> None:
    response = pay(
        client,
        setup["trip_id"],
        setup["ravi_tc"],
        "p-1",
        "500.00",
        method="ONLINE",
        note="phone pay",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trip_customer_id"] == setup["ravi_tc"]
    assert body["reference"] == "p-1"
    assert d(body["amount"]) == Decimal(500)
    assert body["method"] == "ONLINE"
    assert body["kind"] == "PAYMENT"
    assert body["note"] == "phone pay"
    assert body["paid_at"]


@pytest.mark.parametrize(
    "override",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "10.123"},
        {"method": "UPI"},
        {"kind": "LOAN"},
        {"reference": ""},
    ],
)
def test_bad_input_rejected(client, setup, override) -> None:
    body = {
        "reference": "p-1",
        "amount": "100",
        "method": "CASH",
        "kind": "PAYMENT",
        **override,
    }
    response = client.post(
        f"/api/trips/{setup['trip_id']}/customers/{setup['ravi_tc']}/payments",
        json=body,
    )
    assert response.status_code == 422, response.text


def test_same_reference_same_data_replays(client, setup) -> None:
    first = pay(client, setup["trip_id"], setup["ravi_tc"], "p-1", "100")
    second = pay(client, setup["trip_id"], setup["ravi_tc"], "p-1", "100")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    listed = client.get(
        f"/api/trips/{setup['trip_id']}/customers/{setup['ravi_tc']}/payments"
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_same_reference_different_data_conflict(client, setup) -> None:
    pay(client, setup["trip_id"], setup["ravi_tc"], "p-1", "100")
    response = pay(client, setup["trip_id"], setup["ravi_tc"], "p-1", "999")
    assert response.status_code == 409


def test_unknown_trip_customer_404(client, setup) -> None:
    response = pay(client, setup["trip_id"], 99999, "p-1", "100")
    assert response.status_code == 404


def test_trip_customer_of_other_trip_404(client, setup) -> None:
    other_trip = create_trip(client, [setup["rohu"]])
    response = pay(client, other_trip, setup["ravi_tc"], "p-1", "100")
    assert response.status_code == 404


def test_several_payments_listed_in_order(client, setup) -> None:
    pay(client, setup["trip_id"], setup["ravi_tc"], "p-1", "100")
    pay(client, setup["trip_id"], setup["ravi_tc"], "p-2", "200", method="ONLINE")
    pay(client, setup["trip_id"], setup["sunil_tc"], "p-3", "50")

    listed = client.get(
        f"/api/trips/{setup['trip_id']}/customers/{setup['ravi_tc']}/payments"
    )
    assert listed.status_code == 200
    assert [p["reference"] for p in listed.json()] == ["p-1", "p-2"]


# ---------- summary ----------


def test_summary_math(client, priced) -> None:
    trip_id = priced["trip_id"]
    pay(client, trip_id, priced["ravi_tc"], "a-1", "100", kind="ADVANCE")
    pay(client, trip_id, priced["ravi_tc"], "c-1", "300")
    pay(client, trip_id, priced["ravi_tc"], "o-1", "200", method="ONLINE")
    pay(client, trip_id, priced["sunil_tc"], "a-2", "150", kind="ADVANCE")

    body = summary(client, trip_id)

    ravi = row_for(body, priced["ravi_tc"])
    assert d(ravi["billed_amount"]) == Decimal(1000)
    assert ravi["complete"] is True
    assert d(ravi["advance_paid"]) == Decimal(100)
    assert d(ravi["cash_paid"]) == Decimal(400)
    assert d(ravi["online_paid"]) == Decimal(200)
    assert d(ravi["total_paid"]) == Decimal(600)
    assert d(ravi["remaining"]) == Decimal(400)

    sunil = row_for(body, priced["sunil_tc"])
    assert d(sunil["billed_amount"]) == Decimal(0)
    assert d(sunil["total_paid"]) == Decimal(150)
    assert d(sunil["remaining"]) == Decimal(-150)

    assert d(body["billed_amount"]) == Decimal(1000)
    assert d(body["advance_paid"]) == Decimal(250)
    assert d(body["cash_paid"]) == Decimal(550)
    assert d(body["online_paid"]) == Decimal(200)
    assert d(body["total_paid"]) == Decimal(750)
    assert d(body["outstanding"]) == Decimal(400)
    assert d(body["credit"]) == Decimal(150)


def test_advance_before_handover_then_remaining(client, setup, test_session_local) -> None:
    trip_id = setup["trip_id"]
    pay(client, trip_id, setup["ravi_tc"], "a-1", "500", kind="ADVANCE")

    before = row_for(summary(client, trip_id), setup["ravi_tc"])
    assert d(before["remaining"]) == Decimal(-500)

    set_default_rate(test_session_local, trip_id, setup["rohu"], "100")
    post_handover(
        client, trip_id, setup["ravi_tc"], "h-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )

    after = row_for(summary(client, trip_id), setup["ravi_tc"])
    assert d(after["billed_amount"]) == Decimal(1000)
    assert d(after["remaining"]) == Decimal(500)


def test_overpay_is_credit(client, priced) -> None:
    pay(client, priced["trip_id"], priced["ravi_tc"], "p-1", "1200")
    body = summary(client, priced["trip_id"])
    ravi = row_for(body, priced["ravi_tc"])
    assert d(ravi["remaining"]) == Decimal(-200)
    assert d(body["outstanding"]) == Decimal(0)
    assert d(body["credit"]) == Decimal(200)


def test_unpriced_bags_flag_incomplete(client, setup) -> None:
    trip_id = setup["trip_id"]
    post_handover(
        client, trip_id, setup["ravi_tc"], "h-1",
        [{"fish_type_id": setup["rohu"], "bags": 5}],
    )
    pay(client, trip_id, setup["ravi_tc"], "p-1", "100")

    body = summary(client, trip_id)
    ravi = row_for(body, setup["ravi_tc"])
    assert ravi["complete"] is False
    assert d(ravi["billed_amount"]) == Decimal(0)
    assert body["complete"] is False


def test_summary_unknown_trip_404(client) -> None:
    response = client.get("/api/trips/99999/payments-summary")
    assert response.status_code == 404


# ---------- rules ----------


def test_payment_after_close_allowed(client, setup) -> None:
    trip_id = setup["trip_id"]
    record_slip(
        client, trip_id, [{"fish_type_id": setup["rohu"], "delivered_bags": 10}]
    )
    post_handover(
        client, trip_id, setup["ravi_tc"], "h-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    assert close(client, trip_id).status_code == 200

    response = pay(client, trip_id, setup["ravi_tc"], "late-1", "100")
    assert response.status_code == 201, response.text


def test_no_rate_fields_in_responses(client, priced) -> None:
    created = pay(client, priced["trip_id"], priced["ravi_tc"], "p-1", "100")
    listed = client.get(
        f"/api/trips/{priced['trip_id']}/customers/{priced['ravi_tc']}/payments"
    )
    body = summary(client, priced["trip_id"])

    for payload in (created.json(), listed.json(), body):
        assert not any("rate" in key for key in all_keys(payload))


def test_payment_endpoints_need_login(raw_client) -> None:
    post = pay(raw_client, 1, 1, "p-1", "100")
    get = raw_client.get("/api/trips/1/payments-summary")

    assert post.status_code == 401, post.text
    assert get.status_code == 401, get.text
