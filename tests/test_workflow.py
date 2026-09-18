"""End-to-end workflow: request -> admin -> editor -> revision -> production."""
import pytest

from conftest import client_for


@pytest.fixture()
def clients(app):
    return {
        "user": client_for(app, "user@example.com"),
        "admin": client_for(app, "admin@example.com"),
        "editor": client_for(app, "editor@example.com"),
        "production": client_for(app, "production@example.com"),
    }


def status_of(app, request_id):
    from app.models import BookRequest
    with app.app_context():
        return BookRequest.query.get(request_id).status


def make_request(client, book_type_id, title="Buku Uji Alur"):
    res = client.post("/api/requests", json={
        "title": title,
        "book_type_id": book_type_id,
        "description": "Buku untuk pengujian alur kerja.",
        "book_size": "A4",
        "paper_type": "Art Paper 150gr",
        "print_quantity": 50,
        "finishing": "Hard cover",
    })
    assert res.status_code == 201
    return res.get_json()["data"]["request"]["id"]


def full_checklist():
    from app.models import CHECKLIST_FIELDS
    payload = {field: True for field, _ in CHECKLIST_FIELDS}
    payload["note"] = "Seluruh materi sudah sesuai."
    return payload


def test_full_workflow(app, clients, book_type_id):
    user, admin, editor, production = (clients["user"], clients["admin"],
                                       clients["editor"], clients["production"])

    request_id = make_request(user, book_type_id)
    assert status_of(app, request_id) == "DRAFT"

    # Submit requires at least one member.
    assert user.post(f"/api/requests/{request_id}/submit").status_code == 422
    assert user.post(f"/api/requests/{request_id}/members",
                     json={"name": "Anggota Satu"}).status_code == 201

    assert user.post(f"/api/requests/{request_id}/submit").status_code == 200
    assert status_of(app, request_id) == "SUBMITTED"

    assert admin.post(f"/api/admin/requests/{request_id}/review").status_code == 200
    assert status_of(app, request_id) == "ADMIN_REVIEW"

    assert admin.post(f"/api/admin/requests/{request_id}/approve",
                      json={"note": "Lengkap"}).status_code == 200
    assert status_of(app, request_id) == "EDITOR_REVIEW"

    # Editor returns the book for revision; a note is mandatory.
    assert editor.post(f"/api/editor/requests/{request_id}/return",
                       json={"note": ""}).status_code == 422
    assert editor.post(f"/api/editor/requests/{request_id}/return",
                       json={"note": "Foto anggota nomor 1 belum tersedia."}
                       ).status_code == 200
    assert status_of(app, request_id) == "REVISION_REQUIRED"

    # User answers the revision, book goes back to the editor.
    assert user.post(f"/api/requests/{request_id}/revision",
                     json={"response": ""}).status_code == 422
    assert user.post(f"/api/requests/{request_id}/revision",
                     json={"response": "Foto sudah diunggah ulang."}).status_code == 200
    assert status_of(app, request_id) == "EDITOR_REVIEW"

    # Approval is refused while the checklist is incomplete.
    assert editor.post(f"/api/editor/requests/{request_id}/approve").status_code == 422
    assert editor.post(f"/api/editor/requests/{request_id}/review",
                       json=full_checklist()).status_code == 200
    assert editor.post(f"/api/editor/requests/{request_id}/approve").status_code == 200
    assert status_of(app, request_id) == "READY_FOR_PRODUCTION"

    res = admin.post(f"/api/admin/requests/{request_id}/send-to-production", json={})
    assert res.status_code == 200
    assert status_of(app, request_id) == "PRODUCTION"

    order_id = res.get_json()["data"]["request"]["production_order"]["id"]
    assert production.post(f"/api/production/orders/{order_id}/start").status_code == 200
    assert production.post(f"/api/production/orders/{order_id}/quality-check"
                           ).status_code == 200
    assert status_of(app, request_id) == "QUALITY_CHECK"
    assert production.post(f"/api/production/orders/{order_id}/complete").status_code == 200
    assert status_of(app, request_id) == "COMPLETED"

    # Every stage left a history row and an audit entry.
    from app.models import AuditLog, RequestRevision, RequestStatusHistory
    with app.app_context():
        assert RequestStatusHistory.query.filter_by(request_id=request_id).count() >= 10
        assert AuditLog.query.filter_by(request_id=request_id).count() >= 8
        revision = RequestRevision.query.filter_by(request_id=request_id).one()
        assert revision.editor_note.startswith("Foto anggota")
        assert revision.user_response == "Foto sudah diunggah ulang."
        assert revision.resolved_at is not None


def test_revision_history_is_not_overwritten(app, clients, book_type_id):
    """Two revision rounds must leave two separate rows."""
    user, admin, editor = clients["user"], clients["admin"], clients["editor"]
    request_id = make_request(user, book_type_id, "Buku Dua Revisi")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")
    admin.post(f"/api/admin/requests/{request_id}/review")
    admin.post(f"/api/admin/requests/{request_id}/approve", json={})

    for round_no in (1, 2):
        editor.post(f"/api/editor/requests/{request_id}/return",
                    json={"note": f"Perbaikan putaran {round_no}."})
        user.post(f"/api/requests/{request_id}/revision",
                  json={"response": f"Sudah diperbaiki putaran {round_no}."})

    from app.models import RequestRevision
    with app.app_context():
        revisions = (RequestRevision.query.filter_by(request_id=request_id)
                     .order_by(RequestRevision.revision_number).all())
        assert [r.revision_number for r in revisions] == [1, 2]
        assert revisions[0].editor_note == "Perbaikan putaran 1."
        assert revisions[1].editor_note == "Perbaikan putaran 2."


# --------------------------------------------------------------------------
# illegal transitions
# --------------------------------------------------------------------------
def test_user_cannot_skip_to_completed(app, clients, book_type_id):
    """SUBMITTED -> COMPLETED must be impossible through any user-facing route."""
    from app import workflow as wf
    from app.models import BookRequest, User
    from app.services import transition

    user = clients["user"]
    request_id = make_request(user, book_type_id, "Buku Lompat Status")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")

    with app.app_context():
        book_request = BookRequest.query.get(request_id)
        actor = User.query.filter_by(username="user").first()
        with pytest.raises(wf.WorkflowError):
            transition(book_request, wf.COMPLETED, actor)
        assert BookRequest.query.get(request_id).status == "SUBMITTED"


def test_editor_cannot_complete_a_request(app, clients, book_type_id):
    from app import workflow as wf
    from app.models import BookRequest, User
    from app.services import transition

    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Editor Complete")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")
    admin.post(f"/api/admin/requests/{request_id}/review")
    admin.post(f"/api/admin/requests/{request_id}/approve", json={})

    with app.app_context():
        book_request = BookRequest.query.get(request_id)
        editor = User.query.filter_by(username="editor").first()
        with pytest.raises(wf.WorkflowError):
            transition(book_request, wf.COMPLETED, editor)


def test_production_cannot_start_before_admin_sends_it(app, clients, book_type_id):
    """Production must not pull a book that is still in editor review."""
    from app import workflow as wf
    from app.models import BookRequest, User
    from app.services import transition

    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Produksi Dini")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")
    admin.post(f"/api/admin/requests/{request_id}/review")
    admin.post(f"/api/admin/requests/{request_id}/approve", json={})

    with app.app_context():
        book_request = BookRequest.query.get(request_id)
        operator = User.query.filter_by(username="production").first()
        with pytest.raises(wf.WorkflowError):
            transition(book_request, wf.PRODUCTION, operator)


def test_admin_cannot_approve_an_unreviewed_request(app, clients, book_type_id):
    """SUBMITTED -> ADMIN_APPROVED is not a legal edge; review must happen first."""
    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Approve Langsung")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")

    res = admin.post(f"/api/admin/requests/{request_id}/approve", json={})
    assert res.status_code == 409
    assert status_of(app, request_id) == "SUBMITTED"


def test_user_cannot_edit_request_while_in_approval(app, clients, book_type_id):
    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Terkunci")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")
    admin.post(f"/api/admin/requests/{request_id}/review")

    res = user.put(f"/api/requests/{request_id}",
                   json={"title": "Judul Baru", "book_type_id": book_type_id})
    assert res.status_code == 409


def test_reject_and_return_require_a_note(app, clients, book_type_id):
    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Tanpa Alasan")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")
    admin.post(f"/api/admin/requests/{request_id}/review")

    assert admin.post(f"/api/admin/requests/{request_id}/reject",
                      json={"note": "  "}).status_code == 422
    assert admin.post(f"/api/admin/requests/{request_id}/return",
                      json={}).status_code == 422
    assert status_of(app, request_id) == "ADMIN_REVIEW"


def test_notifications_reach_the_next_role(app, clients, book_type_id):
    from app.models import Notification, User

    user, admin = clients["user"], clients["admin"]
    request_id = make_request(user, book_type_id, "Buku Notifikasi")
    user.post(f"/api/requests/{request_id}/members", json={"name": "Anggota"})
    user.post(f"/api/requests/{request_id}/submit")

    with app.app_context():
        admin_user = User.query.filter_by(username="admin").first()
        assert Notification.query.filter_by(user_id=admin_user.id,
                                            request_id=request_id).count() == 1

    admin.post(f"/api/admin/requests/{request_id}/review")
    admin.post(f"/api/admin/requests/{request_id}/approve", json={})

    with app.app_context():
        editor_user = User.query.filter_by(username="editor").first()
        owner = User.query.filter_by(username="user").first()
        assert Notification.query.filter_by(user_id=editor_user.id,
                                            request_id=request_id).count() == 1
        assert Notification.query.filter_by(user_id=owner.id,
                                            request_id=request_id).count() >= 1
