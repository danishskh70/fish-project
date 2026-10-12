def test_list_suppliers_initially_empty(client):
    response = client.get("/api/suppliers/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_supplier(client):
    response = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier A",
            "phone": "9876543210",
            "address": "Pune",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Supplier A"
    assert data["phone"] == "9876543210"
    assert data["address"] == "Pune"
    assert data["is_active"] is True


def test_duplicate_supplier_phone_is_allowed(client):
    payload = {
        "name": "Supplier A",
        "phone": "9876543210",
        "address": "Pune",
    }

    first = client.post("/api/suppliers/", json=payload)

    second = client.post(
        "/api/suppliers/",
        json={
            **payload,
            "name": "Supplier B",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_empty_supplier_fields_are_rejected(client):
    response = client.post(
        "/api/suppliers/",
        json={
            "name": " ",
            "phone": "",
            "address": "Pune",
        },
    )

    assert response.status_code == 422


def test_partial_supplier_update(client):
    created = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier A",
            "phone": "9876543210",
            "address": "Pune",
        },
    ).json()

    response = client.patch(
        f"/api/suppliers/{created['id']}",
        json={"name": "Supplier A Updated"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Supplier A Updated"
    assert data["phone"] == "9876543210"
    assert data["address"] == "Pune"


def test_empty_supplier_update_is_rejected(client):
    created = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier A",
            "phone": "9876543210",
            "address": "Pune",
        },
    ).json()

    response = client.patch(
        f"/api/suppliers/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_update_nonexistent_supplier_returns_404(client):
    response = client.patch(
        "/api/suppliers/999999",
        json={"name": "New Supplier"},
    )

    assert response.status_code == 404


def test_deactivate_supplier_preserves_record(client):
    created = client.post(
        "/api/suppliers/",
        json={
            "name": "Supplier A",
            "phone": "9876543210",
            "address": "Pune",
        },
    ).json()

    response = client.post(
        f"/api/suppliers/{created['id']}/deactivate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    listed = client.get("/api/suppliers/")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["is_active"] is False