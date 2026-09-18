"""File upload validation and secure download."""
import io

from conftest import client_for

# Smallest valid PNG (1x1 pixel).
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a"
    "49444154789c6360000002000100ffff03000006000557bfabd40000000049454e44ae4260 82"
    .replace(" ", ""))


def new_request(client, book_type_id, title="Buku File"):
    return client.post("/api/requests", json={
        "title": title, "book_type_id": book_type_id}).get_json()["data"]["request"]["id"]


def upload(client, request_id, filename, data, category="COVER", content_type=None):
    return client.post(
        f"/api/requests/{request_id}/files",
        data={"file": (io.BytesIO(data), filename, content_type) if content_type
              else (io.BytesIO(data), filename),
              "category": category},
        content_type="multipart/form-data")


def test_valid_image_upload_stores_metadata(app, book_type_id):
    from app.models import BookFile

    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id)
    res = upload(user, request_id, "cover.png", PNG)
    assert res.status_code == 201, res.get_data(as_text=True)

    data = res.get_json()["data"]["file"]
    assert data["original_filename"] == "cover.png"
    assert data["mime_type"] == "image/png"
    assert data["file_size"] == len(PNG)

    with app.app_context():
        stored = BookFile.query.get(data["id"])
        # The stored name must not be the user-supplied one.
        assert stored.stored_filename != "cover.png"
        assert ".." not in stored.file_path


def test_disallowed_extension_is_rejected(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Ekstensi")
    res = upload(user, request_id, "payload.exe", b"MZ binary")
    assert res.status_code == 422
    assert "tidak diizinkan" in res.get_json()["message"]


def test_mime_mismatch_is_rejected(app, book_type_id):
    """A .png announcing itself as something else must not be written."""
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Mime")
    res = upload(user, request_id, "fake.png", PNG, content_type="application/x-msdownload")
    assert res.status_code == 422


def test_empty_file_is_rejected(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Kosong")
    assert upload(user, request_id, "empty.png", b"").status_code == 422


def test_path_traversal_filename_is_sanitised(app, book_type_id):
    from app.models import BookFile

    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Traversal")
    res = upload(user, request_id, "../../evil.png", PNG)
    assert res.status_code == 201
    with app.app_context():
        stored = BookFile.query.get(res.get_json()["data"]["file"]["id"])
        assert "/" not in stored.stored_filename and "\\" not in stored.stored_filename
        assert ".." not in stored.file_path


def test_download_requires_access(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Unduh")
    file_id = upload(user, request_id, "cover.png", PNG).get_json()["data"]["file"]["id"]

    assert user.get(f"/api/files/{file_id}").status_code == 200
    # Staff may read it; an anonymous visitor may not.
    assert client_for(app, "editor@example.com").get(
        f"/api/files/{file_id}").status_code == 200
    assert app.test_client().get(f"/api/files/{file_id}").status_code == 401


def test_user_cannot_upload_final_file(app, book_type_id):
    user = client_for(app, "user@example.com")
    request_id = new_request(user, book_type_id, "Buku Final")
    assert upload(user, request_id, "final.pdf", b"%PDF-1.4 test",
                  category="FINAL").status_code == 403
