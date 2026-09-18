"""Smoke test: every page route renders for the role that owns it."""
import pytest

from conftest import client_for

PUBLIC = ["/", "/about", "/workflow", "/features", "/login"]

PAGES = {
    "user@example.com": ["/user/dashboard", "/user/requests", "/user/requests/new",
                         "/user/revision", "/notifications", "/history", "/profile",
                         "/dashboard"],
    "admin@example.com": ["/admin/dashboard", "/admin/incoming", "/admin/approval",
                          "/admin/editor-queue", "/admin/production-queue",
                          "/admin/books", "/admin/users", "/admin/book-types",
                          "/admin/audit-log", "/notifications", "/history", "/profile"],
    "editor@example.com": ["/editor/dashboard", "/editor/review-queue",
                           "/editor/in-review", "/editor/revision", "/editor/ready",
                           "/notifications", "/history", "/profile"],
    "production@example.com": ["/production/dashboard", "/production/queue",
                               "/production/in-production", "/production/quality-check",
                               "/production/completed", "/notifications", "/history",
                               "/profile"],
}


@pytest.mark.parametrize("url", PUBLIC)
def test_public_pages_render(client, url):
    assert client.get(url).status_code == 200


@pytest.mark.parametrize("identity,url", [
    (identity, url) for identity, urls in PAGES.items() for url in urls
])
def test_dashboard_pages_render(app, identity, url):
    res = client_for(app, identity).get(url)
    # /dashboard redirects to the role's own dashboard.
    assert res.status_code in (200, 302), res.get_data(as_text=True)[:400]


def test_unknown_queue_returns_404(app):
    assert client_for(app, "admin@example.com").get("/admin/bogus").status_code == 404


def test_request_detail_renders_for_owner_and_staff(app, book_type_id):
    user = client_for(app, "user@example.com")
    created = user.post("/api/requests", json={
        "title": "Buku Halaman Detail", "book_type_id": book_type_id}).get_json()
    request_id = created["data"]["request"]["id"]

    assert user.get(f"/requests/{request_id}").status_code == 200
    assert client_for(app, "admin@example.com").get(
        f"/requests/{request_id}").status_code == 200
    assert client_for(app, "editor@example.com").get(
        f"/requests/{request_id}").status_code == 200
