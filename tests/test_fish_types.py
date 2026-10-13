def test_list_fish_types_initially_empty(client):
    response = client.get("/api/fish-types/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_fish_type(client):
    response = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Rohu"
    assert data["is_active"] is True


def test_reject_duplicate_fish_type_name(client):
    first = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    )
    second = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_reject_duplicate_name_during_update(client):
    rohu = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    ).json()

    katla = client.post(
        "/api/fish-types/",
        json={"name": "Katla"},
    ).json()

    response = client.patch(
        f"/api/fish-types/{katla['id']}",
        json={"name": "Rohu"},
    )

    assert response.status_code == 409


def test_update_fish_type_name(client):
    created = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    ).json()

    response = client.patch(
        f"/api/fish-types/{created['id']}",
        json={"name": "Katla"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Katla"


def test_reject_empty_fish_type_name(client):
    response = client.post(
        "/api/fish-types/",
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_deactivate_fish_type(client):
    created = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    ).json()

    response = client.post(
        f"/api/fish-types/{created['id']}/deactivate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_update_nonexistent_fish_type_returns_404(client):
    response = client.patch(
        "/api/fish-types/999999",
        json={"name": "Rohu"},
    )

    assert response.status_code == 404


def test_activate_deactivated_fish_type(client):
    create_response = client.post(
        "/api/fish-types/",
        json={"name": "Rohu"},
    )
    assert create_response.status_code == 201
    fish_type_id = create_response.json()["id"]

    deactivate_response = client.post(
        f"/api/fish-types/{fish_type_id}/deactivate"
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    response = client.post(
        f"/api/fish-types/{fish_type_id}/activate"
    )

    assert response.status_code == 200
    assert response.json()["id"] == fish_type_id
    assert response.json()["is_active"] is True


def test_activate_already_active_fish_type(client):
    create_response = client.post(
        "/api/fish-types/",
        json={"name": "Catla"},
    )
    assert create_response.status_code == 201
    fish_type_id = create_response.json()["id"]

    response = client.post(
        f"/api/fish-types/{fish_type_id}/activate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_activate_nonexistent_fish_type_returns_404(client):
    response = client.post("/api/fish-types/999999/activate")

    assert response.status_code == 404
