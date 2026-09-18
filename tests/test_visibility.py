"""Public visibility toggle for a request's PDF (flipbook on the home page)."""
import io

from conftest import client_for

PDF = b"%PDF-1.4 test content"


def new_request(client, book_type_id, title="Buku Public"):
    return client.post("/api/requests", json={
        "title": title, "book_type_id": book_type_id}).get_json()["data"]["request"]["id"]


def upload_pdf(client, request_id, filename="book.pdf"):
    return client.post(
        f"/api/requests/{request_id}/files",
        data={"file": (io.BytesIO(PDF), filename), "category": "ATTACHMENT"},
        content_type="multipart/form-data")


def test_toggle_requires_pdf(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Tanpa PDF")
    res = user.put(f"/api/requests/{request_id}/visibility", json={"is_public": True})
    assert res.status_code == 422


def test_owner_can_toggle_public(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Dengan PDF")
    assert upload_pdf(user, request_id).status_code == 201

    res = user.put(f"/api/requests/{request_id}/visibility", json={"is_public": True})
    assert res.status_code == 200
    assert res.get_json()["data"]["request"]["is_public"] is True

    anon = app.test_client()
    assert anon.get(f"/books/{request_id}/pdf").status_code == 200

    user.put(f"/api/requests/{request_id}/visibility", json={"is_public": False})
    assert anon.get(f"/books/{request_id}/pdf").status_code == 404


def test_other_roles_cannot_toggle(app, book_type_id):
    owner = client_for(app, "user@example.com")
    request_id = new_request(owner, book_type_id, "Milik Orang Lain")
    upload_pdf(owner, request_id)

    other = client_for(app, "editor@example.com")
    assert other.put(f"/api/requests/{request_id}/visibility",
                     json={"is_public": True}).status_code == 403


def test_public_pdf_hidden_until_made_public(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Belum Public")
    upload_pdf(user, request_id)
    assert app.test_client().get(f"/books/{request_id}/pdf").status_code == 404
