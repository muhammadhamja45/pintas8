"""Authentication tests."""
from conftest import PASSWORD, csrf_for, login


def test_valid_login_returns_role_dashboard(client):
    res = login(client, "admin@example.com")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    assert payload["data"]["user"]["role"] == "ADMIN"
    assert payload["data"]["redirect"] == "/admin/dashboard"


def test_login_with_username_works(client):
    assert login(client, "editor").status_code == 200


def test_invalid_password_is_rejected(client):
    res = login(client, "user@example.com", "wrong-password")
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_unknown_account_is_rejected(client):
    assert login(client, "nobody@example.com").status_code == 401


def test_missing_fields_return_422(client):
    res = client.post("/api/auth/login", json={"identity": "", "password": ""},
                      headers={"X-CSRF-Token": csrf_for(client)})
    assert res.status_code == 422
    assert len(res.get_json()["errors"]) == 2


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    login(client, "user@example.com")
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_password_is_hashed_not_plaintext(app):
    from app.models import User
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        assert user.password_hash != PASSWORD
        assert user.check_password(PASSWORD)


def test_public_home_does_not_require_login(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Book 2 Management" in res.data
