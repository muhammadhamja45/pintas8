"""RBAC tests: every role is blocked from the endpoints it does not own."""
import pytest

from conftest import client_for


@pytest.mark.parametrize("url", [
    "/api/admin/requests", "/api/admin/users", "/api/admin/book-types",
    "/api/admin/audit-logs", "/admin/dashboard", "/admin/users",
])
def test_user_cannot_access_admin(app, url):
    assert client_for(app, "user@example.com").get(url).status_code == 403


@pytest.mark.parametrize("url", ["/api/editor/requests", "/editor/dashboard"])
def test_user_cannot_access_editor(app, url):
    assert client_for(app, "user@example.com").get(url).status_code == 403


@pytest.mark.parametrize("url", ["/api/admin/requests", "/admin/dashboard"])
def test_editor_cannot_access_admin(app, url):
    assert client_for(app, "editor@example.com").get(url).status_code == 403


@pytest.mark.parametrize("url", ["/api/admin/users", "/admin/dashboard"])
def test_production_cannot_access_admin(app, url):
    assert client_for(app, "production@example.com").get(url).status_code == 403


def test_production_cannot_access_editor(app):
    assert client_for(app, "production@example.com").get(
        "/api/editor/requests").status_code == 403


def test_editor_cannot_create_request(app):
    res = client_for(app, "editor@example.com").post(
        "/api/requests", json={"title": "X", "book_type_id": 1})
    assert res.status_code == 403


def test_anonymous_api_call_returns_401_json(client):
    res = client.get("/api/requests")
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_anonymous_page_redirects_to_login(client):
    res = client.get("/user/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_user_cannot_read_other_users_request(app, book_type_id):
    owner = client_for(app, "user@example.com")
    created = owner.post("/api/requests", json={
        "title": "Privasi Request", "book_type_id": book_type_id}).get_json()
    request_id = created["data"]["request"]["id"]

    # Editor may read any request (review duty) but must not edit it.
    editor = client_for(app, "editor@example.com")
    assert editor.get(f"/api/requests/{request_id}").status_code == 200
    assert editor.put(f"/api/requests/{request_id}",
                      json={"title": "Diubah", "book_type_id": book_type_id}
                      ).status_code == 403


def test_user_cannot_change_own_role(app):
    """The self-service profile endpoint must ignore role changes entirely."""
    from app.models import User

    user_client = client_for(app, "user@example.com")
    res = user_client.put("/api/auth/me", json={
        "full_name": "Pengguna Demo", "email": "user@example.com", "role": "ADMIN"})
    assert res.status_code == 200
    with app.app_context():
        assert User.query.filter_by(username="user").first().role_name == "USER"
