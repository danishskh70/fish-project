from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.handover import Handover, HandoverLine
from app.models.trip_customer import TripCustomer
from app.models.trip_customer_rate import TripCustomerRate
from app.models.trip_fish_type import TripFishType


def create_fish_type(client, name):
    response = client.post("/api/fish-types/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_supplier(client):
    response = client.post(
        "/api/suppliers/",
        json={"name": "Rate Supplier", "phone": "9890000004", "address": "Pune"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_customer(client, name):
    response = client.post(
        "/api/customers/",
        json={"name": name, "phone": "9000000002", "address": "Loni"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_trip(client, fish_type_ids):
    response = client.post(
        "/api/trips/",
        json={
            "trip_date": "2026-10-20",
            "supplier_id": create_supplier(client),
            "fish_type_ids": fish_type_ids,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_trip_customer(session_factory, trip_id, customer_id):
    with session_factory() as db:
        trip_customer = TripCustomer(trip_id=trip_id, customer_id=customer_id)
        db.add(trip_customer)
        db.commit()
        return trip_customer.id


def put_rates(client, trip_id, rates):
    return client.put(f"/api/trips/{trip_id}/rates", json={"rates": rates})


def put_customer_rates(client, trip_id, trip_customer_id, rates):
    return client.put(
        f"/api/trips/{trip_id}/customers/{trip_customer_id}/rates",
        json={"rates": rates},
    )


def post_handover(client, trip_id, trip_customer_id, reference, lines):
    response = client.post(
        f"/api/trips/{trip_id}/handovers",
        json={
            "trip_customer_id": trip_customer_id,
            "submit_reference": reference,
            "lines": lines,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def default_rate(session_factory, trip_id, fish_type_id):
    with session_factory() as db:
        return db.scalar(
            select(TripFishType.rate_per_bag).where(
                TripFishType.trip_id == trip_id,
                TripFishType.fish_type_id == fish_type_id,
            )
        )


def override_rate(session_factory, trip_customer_id, fish_type_id):
    with session_factory() as db:
        return db.scalar(
            select(TripCustomerRate.rate_per_bag).where(
                TripCustomerRate.trip_customer_id == trip_customer_id,
                TripCustomerRate.fish_type_id == fish_type_id,
            )
        )


def line_rate(session_factory, trip_customer_id, fish_type_id):
    with session_factory() as db:
        return db.scalar(
            select(HandoverLine.rate_per_bag)
            .join(Handover, Handover.id == HandoverLine.handover_id)
            .where(
                Handover.trip_customer_id == trip_customer_id,
                HandoverLine.fish_type_id == fish_type_id,
            )
        )


@pytest.fixture
def setup(client, test_session_local):
    rohu = create_fish_type(client, "Rate Rohu")
    katla = create_fish_type(client, "Rate Katla")
    trip_id = create_trip(client, [rohu, katla])
    ravi_tc = add_trip_customer(
        test_session_local, trip_id, create_customer(client, "Ravi")
    )
    sunil_tc = add_trip_customer(
        test_session_local, trip_id, create_customer(client, "Sunil")
    )
    return {
        "rohu": rohu,
        "katla": katla,
        "trip_id": trip_id,
        "ravi_tc": ravi_tc,
        "sunil_tc": sunil_tc,
    }


# ---------- trip default rates ----------

def test_set_default_rates_response_has_no_number(client, setup):
    response = put_rates(
        client,
        setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "rate_per_bag": 50},
            {"fish_type_id": setup["katla"], "rate_per_bag": 80},
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {"fish_type_id": setup["rohu"], "rate_set": True},
        {"fish_type_id": setup["katla"], "rate_set": True},
    ]
    assert "50" not in response.text
    assert "80" not in response.text


def test_default_rate_is_stored(client, setup, test_session_local):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    stored = default_rate(test_session_local, setup["trip_id"], setup["rohu"])
    assert stored == Decimal(50)
    assert default_rate(
        test_session_local, setup["trip_id"], setup["katla"]
    ) is None


def test_setting_again_overwrites(client, setup, test_session_local):
    rates = [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}]
    put_rates(client, setup["trip_id"], rates)
    rates[0]["rate_per_bag"] = 55
    assert put_rates(client, setup["trip_id"], rates).status_code == 200
    assert default_rate(
        test_session_local, setup["trip_id"], setup["rohu"]
    ) == Decimal(55)


def test_zero_rate_allowed(client, setup, test_session_local):
    response = put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 0}],
    )
    assert response.status_code == 200
    assert default_rate(
        test_session_local, setup["trip_id"], setup["rohu"]
    ) == Decimal(0)


@pytest.mark.parametrize("rate", [-1, -0.5, 10.555])
def test_bad_rate_rejected(client, setup, rate):
    response = put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": rate}],
    )
    assert response.status_code == 422


def test_duplicate_and_empty_rejected(client, setup):
    duplicate = put_rates(
        client, setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "rate_per_bag": 1},
            {"fish_type_id": setup["rohu"], "rate_per_bag": 2},
        ],
    )
    assert duplicate.status_code == 422
    assert put_rates(client, setup["trip_id"], []).status_code == 422


def test_unknown_trip_404(client, setup):
    response = put_rates(
        client, 99999, [{"fish_type_id": setup["rohu"], "rate_per_bag": 1}]
    )
    assert response.status_code == 404


def test_fish_not_on_trip_404(client, setup, test_session_local):
    other = create_fish_type(client, "Rate Mrigal")
    response = put_rates(
        client, setup["trip_id"], [{"fish_type_id": other, "rate_per_bag": 1}]
    )
    assert response.status_code == 404
    assert default_rate(test_session_local, setup["trip_id"], other) is None


def test_failed_batch_saves_nothing(client, setup, test_session_local):
    response = put_rates(
        client, setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "rate_per_bag": 50},
            {"fish_type_id": 99999, "rate_per_bag": 1},
        ],
    )
    assert response.status_code == 404
    assert default_rate(
        test_session_local, setup["trip_id"], setup["rohu"]
    ) is None


# ---------- customer overrides ----------

def test_override_stored_and_response_has_no_number(
    client, setup, test_session_local
):
    response = put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {"fish_type_id": setup["rohu"], "rate_set": True}
    ]
    assert "45" not in response.text
    assert override_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(45)


def test_override_overwrites(client, setup, test_session_local):
    for rate in (45, 48):
        put_customer_rates(
            client, setup["trip_id"], setup["ravi_tc"],
            [{"fish_type_id": setup["rohu"], "rate_per_bag": rate}],
        )
    assert override_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(48)


def test_override_for_trip_customer_of_other_trip_404(
    client, setup, test_session_local
):
    other_trip = create_trip(client, [setup["rohu"]])
    other_tc = add_trip_customer(
        test_session_local, other_trip, create_customer(client, "Elsewhere")
    )
    response = put_customer_rates(
        client, setup["trip_id"], other_tc,
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )
    assert response.status_code == 404


def test_override_fish_not_on_trip_404(client, setup):
    other = create_fish_type(client, "Rate Common")
    response = put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": other, "rate_per_bag": 45}],
    )
    assert response.status_code == 404


# ---------- rate status ----------

def test_rate_status_shows_flags_not_numbers(client, setup):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )

    response = client.get(f"/api/trips/{setup['trip_id']}/rate-status")
    assert response.status_code == 200, response.text
    rows = {row["fish_type_id"]: row for row in response.json()}
    assert rows[setup["rohu"]]["default_set"] is True
    assert rows[setup["rohu"]]["override_trip_customer_ids"] == [
        setup["ravi_tc"]
    ]
    assert rows[setup["katla"]]["default_set"] is False
    assert rows[setup["katla"]]["override_trip_customer_ids"] == []
    for row in rows.values():
        assert set(row) == {
            "fish_type_id",
            "fish_type_name",
            "default_set",
            "override_trip_customer_ids",
        }


def test_rate_status_unknown_trip_404(client):
    assert client.get("/api/trips/99999/rate-status").status_code == 404


# ---------- pricing late ----------

def test_default_prices_unpriced_lines(client, setup, test_session_local):
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) is None

    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(50)


def test_override_prices_only_that_customer_then_default_skips_override(
    client, setup, test_session_local
):
    for tc, ref in ((setup["ravi_tc"], "ref-r"), (setup["sunil_tc"], "ref-s")):
        post_handover(
            client, setup["trip_id"], tc, ref,
            [{"fish_type_id": setup["rohu"], "bags": 10}],
        )

    put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(45)
    assert line_rate(
        test_session_local, setup["sunil_tc"], setup["rohu"]
    ) is None

    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    assert line_rate(
        test_session_local, setup["sunil_tc"], setup["rohu"]
    ) == Decimal(50)
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(45)

# ---------- rate saved on handover line ----------

def test_handover_saves_override_else_default(
    client, setup, test_session_local
):
    put_rates(
        client, setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "rate_per_bag": 50},
            {"fish_type_id": setup["katla"], "rate_per_bag": 80},
        ],
    )
    put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )

    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-r",
        [
            {"fish_type_id": setup["rohu"], "bags": 10},
            {"fish_type_id": setup["katla"], "bags": 5},
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-s",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )

    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(45)
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["katla"]
    ) == Decimal(80)
    assert line_rate(
        test_session_local, setup["sunil_tc"], setup["rohu"]
    ) == Decimal(50)


def test_rate_change_never_touches_priced_lines(
    client, setup, test_session_local
):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )

    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 55}],
    )
    assert line_rate(
        test_session_local, setup["sunil_tc"], setup["rohu"]
    ) == Decimal(50)

    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-2",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) == Decimal(55)


def test_handover_without_rate_is_unpriced(client, setup, test_session_local):
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    assert line_rate(
        test_session_local, setup["ravi_tc"], setup["rohu"]
    ) is None


def test_no_rate_in_handover_stock_or_totals(client, setup):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )
    created = client.post(
        f"/api/trips/{setup['trip_id']}/handovers",
        json={
            "trip_customer_id": setup["ravi_tc"],
            "submit_reference": "ref-1",
            "lines": [{"fish_type_id": setup["rohu"], "bags": 10}],
        },
    )
    trip = setup["trip_id"]
    responses = [
        created,
        client.get(f"/api/trips/{trip}/handovers"),
        client.get(f"/api/trips/{trip}/handovers/{created.json()['id']}"),
        client.get(f"/api/trips/{trip}/stock"),
        client.get(f"/api/trips/{trip}/handover-totals"),
    ]
    for response in responses:
        assert response.status_code in (200, 201), response.text
        assert "rate_per_bag" not in response.text
        assert "45" not in response.text.replace("10", "")

# ---------- bill ----------

def get_bill(client, trip_id):
    response = client.get(f"/api/trips/{trip_id}/bill")
    assert response.status_code == 200, response.text
    return response.json()


def bill_by_customer(bill):
    return {row["trip_customer_id"]: row for row in bill["customers"]}


def test_bill_example_ravi_and_sunil(client, setup):
    put_rates(
        client, setup["trip_id"],
        [
            {"fish_type_id": setup["rohu"], "rate_per_bag": 50},
            {"fish_type_id": setup["katla"], "rate_per_bag": 80},
        ],
    )
    put_customer_rates(
        client, setup["trip_id"], setup["ravi_tc"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 45}],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-r",
        [
            {"fish_type_id": setup["rohu"], "bags": 10},
            {"fish_type_id": setup["katla"], "bags": 5},
        ],
    )
    post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-s",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )

    bill = get_bill(client, setup["trip_id"])
    rows = bill_by_customer(bill)
    assert Decimal(rows[setup["ravi_tc"]]["total_amount"]) == Decimal(850)
    assert Decimal(rows[setup["sunil_tc"]]["total_amount"]) == Decimal(500)
    assert rows[setup["ravi_tc"]]["total_bags"] == 15
    assert rows[setup["ravi_tc"]]["complete"] is True
    assert Decimal(bill["total_amount"]) == Decimal(1350)
    assert bill["total_bags"] == 25
    assert bill["unpriced_bags"] == 0
    assert bill["complete"] is True


def test_default_change_keeps_old_bills_and_prices_new_handovers(
    client, setup
):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 55}],
    )

    rows = bill_by_customer(get_bill(client, setup["trip_id"]))
    assert Decimal(rows[setup["sunil_tc"]]["total_amount"]) == Decimal(500)

    post_handover(
        client, setup["trip_id"], setup["sunil_tc"], "ref-2",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    rows = bill_by_customer(get_bill(client, setup["trip_id"]))
    assert Decimal(rows[setup["sunil_tc"]]["total_amount"]) == Decimal(1050)


def test_unpriced_lines_make_bill_incomplete_then_complete(client, setup):
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    bill = get_bill(client, setup["trip_id"])
    row = bill_by_customer(bill)[setup["ravi_tc"]]
    assert row["unpriced_bags"] == 10
    assert Decimal(row["total_amount"]) == Decimal(0)
    assert row["complete"] is False
    assert bill["complete"] is False

    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    bill = get_bill(client, setup["trip_id"])
    row = bill_by_customer(bill)[setup["ravi_tc"]]
    assert row["unpriced_bags"] == 0
    assert Decimal(row["total_amount"]) == Decimal(500)
    assert row["complete"] is True
    assert bill["complete"] is True


def test_mixed_priced_and_unpriced_lines(client, setup):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [
            {"fish_type_id": setup["rohu"], "bags": 10},
            {"fish_type_id": setup["katla"], "bags": 4},
        ],
    )
    row = bill_by_customer(get_bill(client, setup["trip_id"]))[
        setup["ravi_tc"]
    ]
    assert Decimal(row["total_amount"]) == Decimal(500)
    assert row["unpriced_bags"] == 4
    assert row["total_bags"] == 14
    assert row["complete"] is False


def test_zero_bag_unpriced_line_is_not_incomplete(client, setup):
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 0}],
    )
    row = bill_by_customer(get_bill(client, setup["trip_id"]))[
        setup["ravi_tc"]
    ]
    assert row["unpriced_bags"] == 0
    assert row["complete"] is True


def test_customer_without_handover_not_listed(client, setup):
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 1}],
    )
    rows = bill_by_customer(get_bill(client, setup["trip_id"]))
    assert setup["sunil_tc"] not in rows


def test_empty_bill(client, setup):
    bill = get_bill(client, setup["trip_id"])
    assert bill["customers"] == []
    assert bill["total_bags"] == 0
    assert Decimal(bill["total_amount"]) == Decimal(0)
    assert bill["complete"] is True


def test_bill_has_no_rate_fields(client, setup):
    put_rates(
        client, setup["trip_id"],
        [{"fish_type_id": setup["rohu"], "rate_per_bag": 50}],
    )
    post_handover(
        client, setup["trip_id"], setup["ravi_tc"], "ref-1",
        [{"fish_type_id": setup["rohu"], "bags": 10}],
    )
    bill = get_bill(client, setup["trip_id"])
    assert set(bill) == {
        "trip_id", "customers", "total_bags",
        "unpriced_bags", "total_amount", "complete",
    }
    assert set(bill["customers"][0]) == {
        "trip_customer_id", "customer_id", "total_bags",
        "unpriced_bags", "total_amount", "complete",
    }
    assert "rate" not in client.get(
        f"/api/trips/{setup['trip_id']}/bill"
    ).text


def test_bill_unknown_trip_404(client):
    assert client.get("/api/trips/99999/bill").status_code == 404