def test_list_customers_initially_empty(client):
    response = client.get("/api/customers/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_customer(client):
    response = client.post(
        "/api/customers/",
        json={
            "name": "Danish",
            "phone": "9890456123",
            "address": "Ghargoan",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Danish"
    assert data["phone"] == "9890456123"
    assert data["address"] == "Ghargoan"
    assert data["is_active"] is True


def test_duplicate_customer_phone_is_allowed(client):
    payload = {
        "name": "Danish",
        "phone": "9890456123",
        "address": "Ghargoan",
    }

    first = client.post("/api/customers/", json=payload)

    second = client.post(
        "/api/customers/",
        json={
            **payload,
            "name": "Jiyan",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_empty_customer_fields_are_rejected(client):
    response = client.post(
        "/api/customers/",
        json={
            "name": " ",
            "phone": "",
            "address": "Ghargoan",
        },
    )

    assert response.status_code == 422


def test_partial_customer_update(client):
    created = client.post(
        "/api/customers/",
        json={
            "name": "Danish",
            "phone": "9890456123",
            "address": "Ghargoan",
        },
    ).json()

    response = client.patch(
        f"/api/customers/{created['id']}",
        json={"name": "Danish Alam"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Danish Alam"
    assert data["phone"] == "9890456123"
    assert data["address"] == "Ghargoan"


def test_empty_customer_patch_is_rejected(client):
    created = client.post(
        "/api/customers/",
        json={
            "name": "Danish",
            "phone": "9890456123",
            "address": "Ghargoan",
        },
    ).json()

    response = client.patch(
        f"/api/customers/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_update_nonexistent_customer_returns_404(client):
    response = client.patch(
        "/api/customers/999999",
        json={"name": "New Name"},
    )

    assert response.status_code == 404


def test_deactivate_customer(client):
    created = client.post(
        "/api/customers/",
        json={
            "name": "Danish",
            "phone": "9890456123",
            "address": "Ghargoan",
        },
    ).json()

    response = client.post(
        f"/api/customers/{created['id']}/deactivate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Deactivation must not delete the record.
    listed = client.get("/api/customers/")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["is_active"] is False


def test_activate_deactivated_customer(client):
    create_response = client.post(
        "/api/customers/",
        json={
            "name": "Danish",
            "phone": "9890456123",
            "address": "Ghargoan",
        },
    )
    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    deactivate_response = client.post(
        f"/api/customers/{customer_id}/deactivate"
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    response = client.post(
        f"/api/customers/{customer_id}/activate"
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer_id
    assert response.json()["is_active"] is True


def test_activate_already_active_customer(client):
    create_response = client.post(
        "/api/customers/",
        json={
            "name": "Test Customer",
            "phone": "9890456124",
            "address": "Pune",
        },
    )
    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    response = client.post(
        f"/api/customers/{customer_id}/activate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_activate_nonexistent_customer_returns_404(client):
    response = client.post("/api/customers/999999/activate")

    assert response.status_code == 404
