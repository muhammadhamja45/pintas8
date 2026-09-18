"""Editor API: checklist, revision request, final approval."""
from flask import Blueprint, abort, request

from . import fail, ok
from .. import workflow as wf
from ..extensions import db
from ..models import CHECKLIST_FIELDS, BookRequest, EditorChecklist, RequestRevision
from ..security import current_user, role_required
from ..services import (audit, notify, notify_role, paginated_payload,
                        query_requests, transition)

bp = Blueprint("api_editor", __name__, url_prefix="/api/editor")

EDITOR_STATUSES = [wf.EDITOR_REVIEW, wf.REVISION_REQUIRED, wf.USER_REVISION,
                   wf.EDITOR_APPROVED, wf.READY_FOR_PRODUCTION]


def get_request_or_404(request_id):
    obj = BookRequest.query.get(request_id)
    if obj is None:
        abort(404, description="Request tidak ditemukan.")
    return obj


@bp.get("/requests")
@role_required("EDITOR")
def list_requests():
    args = request.args
    statuses = args.getlist("status") or EDITOR_STATUSES
    pagination = query_requests(
        statuses=statuses,
        search=args.get("q"),
        book_type_id=args.get("book_type_id", type=int),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        sort=args.get("sort", "updated_at"),
        direction=args.get("direction", "desc"),
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", 10, type=int),
    )
    return ok("OK", paginated_payload(pagination))


@bp.get("/requests/<int:request_id>")
@role_required("EDITOR")
def get_request(request_id):
    return ok("OK", {"request": get_request_or_404(request_id).to_dict(detail=True)})


@bp.post("/requests/<int:request_id>/review")
@role_required("EDITOR")
def save_review(request_id):
    """Persist the editor checklist. Creates it on first save."""
    book_request = get_request_or_404(request_id)
    editor = current_user()
    if book_request.status != wf.EDITOR_REVIEW:
        return fail("Request tidak sedang dalam pemeriksaan editor.", code=409)

    payload = request.get_json(silent=True) or {}
    checklist = book_request.checklist
    if checklist is None:
        checklist = EditorChecklist(request_id=book_request.id, editor_id=editor.id)
        db.session.add(checklist)
    else:
        checklist.editor_id = editor.id

    for field, _ in CHECKLIST_FIELDS:
        if field in payload:
            setattr(checklist, field, bool(payload[field]))
    if "note" in payload:
        checklist.note = (payload.get("note") or "").strip() or None

    if book_request.current_assignee_id != editor.id:
        book_request.current_assignee_id = editor.id

    audit("START_REVIEW", user=editor, request_obj=book_request,
          new_status=book_request.status, description="Checklist editor disimpan")
    db.session.commit()
    return ok("Checklist disimpan.", {"checklist": checklist.to_dict()})


@bp.post("/requests/<int:request_id>/return")
@role_required("EDITOR")
def return_for_revision(request_id):
    """EDITOR_REVIEW -> REVISION_REQUIRED. Note is mandatory and kept as history."""
    book_request = get_request_or_404(request_id)
    editor = current_user()
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return fail("Catatan revisi wajib diisi.",
                    ["Jelaskan apa yang harus diperbaiki user."], 422)

    try:
        old = transition(book_request, wf.REVISION_REQUIRED, editor, note=note,
                         assignee=book_request.owner)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    book_request.revision_count += 1
    db.session.add(RequestRevision(
        request_id=book_request.id, revision_number=book_request.revision_count,
        requested_by=editor.id, editor_note=note))

    notify(book_request.user_id, "Request dikembalikan Editor",
           f"Request {book_request.request_code} perlu revisi. Catatan: {note}",
           book_request.id, "WARNING")
    audit("REQUEST_REVISION", user=editor, request_obj=book_request, old_status=old,
          new_status=wf.REVISION_REQUIRED,
          description=f"Revisi #{book_request.revision_count}: {note}")
    db.session.commit()
    return ok("Request dikembalikan untuk revisi.",
              {"request": book_request.to_dict(detail=True)})


@bp.post("/requests/<int:request_id>/approve")
@role_required("EDITOR")
def approve(request_id):
    """EDITOR_REVIEW -> EDITOR_APPROVED -> READY_FOR_PRODUCTION.

    Refuses while the checklist is incomplete: production must not receive a
    book whose printing specs were never confirmed.
    """
    book_request = get_request_or_404(request_id)
    editor = current_user()
    checklist = book_request.checklist
    if checklist is None or not checklist.all_checked:
        missing = [label for field, label in CHECKLIST_FIELDS
                   if not (checklist and getattr(checklist, field))]
        return fail("Checklist editor belum lengkap.", missing, 422)

    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None
    try:
        old = transition(book_request, wf.EDITOR_APPROVED, editor,
                         note=note or "Pemeriksaan editor selesai")
        transition(book_request, wf.READY_FOR_PRODUCTION, editor,
                   note="Siap untuk produksi", assignee=None)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    notify_role("ADMIN", "Pemeriksaan editor selesai",
                f"{book_request.request_code} siap diproduksi.", book_request.id, "SUCCESS")
    notify(book_request.user_id, "Request lolos pemeriksaan editor",
           f"Request {book_request.request_code} telah disetujui editor dan "
           "menunggu proses produksi.", book_request.id, "SUCCESS")
    audit("EDITOR_APPROVE", user=editor, request_obj=book_request, old_status=old,
          new_status=wf.READY_FOR_PRODUCTION, description=note or "Disetujui editor")
    db.session.commit()
    return ok("Request disetujui dan siap produksi.", {"request": book_request.to_dict()})
