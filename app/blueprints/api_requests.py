"""User-facing request API: CRUD, members, texts, files, submit, revision."""
import os
from datetime import datetime

from flask import Blueprint, abort, current_app, request, send_file

from . import fail, ok
from .. import workflow as wf
from ..extensions import db
from ..models import (BookFile, BookMember, BookRequest, BookText, BookType,
                      RequestRevision, RequestStatusHistory)
from ..security import (UploadError, current_user, login_required, resolve_upload_path,
                        role_required, save_upload)
from ..services import (audit, first_user_with_role, new_request_code, notify,
                        notify_role, paginated_payload, query_requests, transition)

bp = Blueprint("api_requests", __name__, url_prefix="/api")

VALID_SECTIONS = {"KATA_PENGANTAR", "DESKRIPSI", "BIODATA", "ISI_BUKU",
                  "CATATAN_LAYOUT", "INSTRUKSI_PERCETAKAN"}


# --------------------------------------------------------------------------
# access helpers
# --------------------------------------------------------------------------
def get_request_or_404(request_id):
    obj = BookRequest.query.get(request_id)
    if obj is None:
        abort(404, description="Request tidak ditemukan.")
    return obj


def ensure_can_view(book_request):
    """Owner sees their own; ADMIN/EDITOR/PRODUCTION see all (read-only scope)."""
    user = current_user()
    if user.role_name in ("ADMIN", "EDITOR", "PRODUCTION"):
        return
    if book_request.user_id != user.id:
        abort(403, description="Anda tidak memiliki akses ke request ini.")


def ensure_owner(book_request):
    """Owner-only check with no status restriction (unlike ensure_owner_editable)."""
    if book_request.user_id != current_user().id:
        abort(403, description="Anda hanya dapat mengubah request milik sendiri.")


def ensure_owner_editable(book_request):
    """Content edits: owner only, and only while the workflow allows it."""
    user = current_user()
    if book_request.user_id != user.id:
        abort(403, description="Anda hanya dapat mengubah request milik sendiri.")
    if book_request.status not in wf.USER_EDITABLE:
        abort(409, description=(
            "Request sedang dalam proses dan tidak dapat diubah. "
            "Perubahan hanya dapat dilakukan saat draft atau revisi."))


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        abort(422, description="Format tanggal harus YYYY-MM-DD.")


def apply_fields(book_request, payload):
    errors = []
    title = (payload.get("title") or "").strip()
    if not title:
        errors.append("Judul buku wajib diisi.")
    elif len(title) > 200:
        errors.append("Judul buku maksimal 200 karakter.")

    book_type_id = payload.get("book_type_id")
    book_type = BookType.query.get(book_type_id) if book_type_id else None
    if book_type is None or not book_type.is_active:
        errors.append("Jenis buku tidak valid.")

    quantity = payload.get("print_quantity")
    if quantity not in (None, "",):
        try:
            quantity = int(quantity)
            if quantity <= 0:
                errors.append("Jumlah cetak harus lebih dari 0.")
        except (TypeError, ValueError):
            errors.append("Jumlah cetak harus berupa angka.")
    else:
        quantity = None

    if errors:
        return errors

    book_request.title = title
    book_request.book_type_id = book_type.id
    book_request.description = (payload.get("description") or "").strip() or None
    book_request.deadline = parse_date(payload.get("deadline"))
    book_request.extra_note = (payload.get("extra_note") or "").strip() or None
    book_request.book_size = (payload.get("book_size") or "").strip() or None
    book_request.paper_type = (payload.get("paper_type") or "").strip() or None
    book_request.print_quantity = quantity
    book_request.finishing = (payload.get("finishing") or "").strip() or None
    book_request.printing_note = (payload.get("printing_note") or "").strip() or None
    return []


# --------------------------------------------------------------------------
# requests
# --------------------------------------------------------------------------
@bp.get("/requests")
@role_required("USER")
def list_requests():
    args = request.args
    pagination = query_requests(
        user_id=current_user().id,
        statuses=args.getlist("status") or None,
        search=args.get("q"),
        book_type_id=args.get("book_type_id", type=int),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        sort=args.get("sort", "created_at"),
        direction=args.get("direction", "desc"),
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", 10, type=int),
    )
    return ok("OK", paginated_payload(pagination))


@bp.post("/requests")
@role_required("USER")
def create_request():
    payload = request.get_json(silent=True) or {}
    user = current_user()
    book_request = BookRequest(user_id=user.id, request_code=new_request_code(),
                               status=wf.DRAFT, book_type_id=0)
    errors = apply_fields(book_request, payload)
    if errors:
        return fail("Data request belum lengkap.", errors, 422)

    db.session.add(book_request)
    db.session.flush()
    db.session.add(RequestStatusHistory(
        request_id=book_request.id, user_id=user.id,
        old_status=None, new_status=wf.DRAFT, note="Request dibuat"))
    audit("CREATE_REQUEST", user=user, request_obj=book_request, new_status=wf.DRAFT,
          description=f"Membuat request {book_request.request_code}")
    db.session.commit()
    return ok("Request berhasil dibuat.", {"request": book_request.to_dict(detail=True)}, 201)


@bp.get("/requests/<int:request_id>")
@login_required
def get_request(request_id):
    book_request = get_request_or_404(request_id)
    ensure_can_view(book_request)
    return ok("OK", {"request": book_request.to_dict(detail=True)})


@bp.put("/requests/<int:request_id>")
@role_required("USER")
def update_request(request_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    errors = apply_fields(book_request, request.get_json(silent=True) or {})
    if errors:
        return fail("Data request belum lengkap.", errors, 422)
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description=f"Memperbarui {book_request.request_code}")
    db.session.commit()
    return ok("Request berhasil disimpan.", {"request": book_request.to_dict(detail=True)})


@bp.post("/requests/<int:request_id>/submit")
@role_required("USER")
def submit_request(request_id):
    book_request = get_request_or_404(request_id)
    user = current_user()
    if book_request.user_id != user.id:
        abort(403, description="Anda hanya dapat submit request milik sendiri.")
    if book_request.status != wf.DRAFT:
        return fail("Hanya request berstatus Draft yang dapat disubmit.", code=409)
    if not book_request.members:
        return fail("Tambahkan minimal satu anggota sebelum submit.", code=422)

    try:
        old = transition(book_request, wf.SUBMITTED, user, note="Request disubmit oleh user")
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    notify_role("ADMIN", "Request buku baru",
                f"{user.full_name} mengajukan request {book_request.request_code} - "
                f"{book_request.title}.", book_request.id, "INFO")
    audit("SUBMIT_REQUEST", user=user, request_obj=book_request, old_status=old,
          new_status=wf.SUBMITTED, description="Request disubmit")
    db.session.commit()
    return ok("Request berhasil disubmit.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/revision")
@role_required("USER")
def submit_revision(request_id):
    """User answers the editor's revision note and sends the book back for review."""
    book_request = get_request_or_404(request_id)
    user = current_user()
    if book_request.user_id != user.id:
        abort(403, description="Anda hanya dapat merevisi request milik sendiri.")
    if book_request.status not in (wf.REVISION_REQUIRED, wf.USER_REVISION):
        return fail("Request ini tidak sedang dalam status revisi.", code=409)

    response = (request.get_json(silent=True) or {}).get("response", "").strip()
    if not response:
        return fail("Catatan perbaikan wajib diisi.", ["Tuliskan apa yang sudah diperbaiki."], 422)

    revision = (RequestRevision.query
                .filter_by(request_id=book_request.id, resolved_at=None)
                .order_by(RequestRevision.revision_number.desc())
                .first())
    if revision is None:
        return fail("Tidak ada revisi terbuka untuk request ini.", code=409)

    if book_request.status == wf.REVISION_REQUIRED:
        transition(book_request, wf.USER_REVISION, user, note="User memulai revisi")

    revision.user_response = response
    revision.resolved_by = user.id
    revision.resolved_at = datetime.now()

    editor = first_user_with_role("EDITOR")
    try:
        old = transition(book_request, wf.EDITOR_REVIEW, user,
                         note=f"Revisi #{revision.revision_number} dikirim: {response}",
                         assignee=editor)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    notify_role("EDITOR", "Revisi dikirim user",
                f"{book_request.request_code} telah direvisi dan menunggu pemeriksaan ulang.",
                book_request.id, "INFO")
    audit("SUBMIT_REVISION", user=user, request_obj=book_request, old_status=old,
          new_status=wf.EDITOR_REVIEW,
          description=f"Revisi #{revision.revision_number} dikirim")
    db.session.commit()
    return ok("Revisi berhasil dikirim.", {"request": book_request.to_dict(detail=True)})


@bp.put("/requests/<int:request_id>/visibility")
@role_required("USER")
def set_visibility(request_id):
    """Owner toggles whether this request's PDF is shown publicly on the home page."""
    book_request = get_request_or_404(request_id)
    ensure_owner(book_request)
    is_public = bool((request.get_json(silent=True) or {}).get("is_public"))
    if is_public and book_request.pdf_file is None:
        return fail("Upload PDF isi buku terlebih dahulu.", code=422)
    book_request.is_public = is_public
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description=("Menampilkan request secara public" if is_public
                       else "Menyembunyikan request dari public"))
    db.session.commit()
    return ok("Visibilitas berhasil diperbarui.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/cancel")
@role_required("USER")
def cancel_request(request_id):
    book_request = get_request_or_404(request_id)
    user = current_user()
    if book_request.user_id != user.id:
        abort(403, description="Anda hanya dapat membatalkan request milik sendiri.")
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return fail("Alasan pembatalan wajib diisi.", code=422)
    try:
        old = transition(book_request, wf.CANCELLED, user, note=note)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)
    audit("CANCEL_REQUEST", user=user, request_obj=book_request, old_status=old,
          new_status=wf.CANCELLED, description=note)
    db.session.commit()
    return ok("Request dibatalkan.", {"request": book_request.to_dict()})


# --------------------------------------------------------------------------
# members
# --------------------------------------------------------------------------
@bp.post("/requests/<int:request_id>/members")
@role_required("USER")
def add_member(request_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return fail("Nama anggota wajib diisi.", code=422)

    member = BookMember(
        request_id=book_request.id, name=name,
        position=(payload.get("position") or "").strip() or None,
        note=(payload.get("note") or "").strip() or None,
        photo_file_id=payload.get("photo_file_id") or None,
        sort_order=len(book_request.members))
    db.session.add(member)
    db.session.flush()
    book_request.member_count = BookMember.query.filter_by(request_id=book_request.id).count()
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description=f"Menambah anggota {name}")
    db.session.commit()
    return ok("Anggota ditambahkan.", {"member": member.to_dict()}, 201)


@bp.put("/requests/<int:request_id>/members/<int:member_id>")
@role_required("USER")
def update_member(request_id, member_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    member = BookMember.query.filter_by(id=member_id, request_id=book_request.id).first()
    if member is None:
        abort(404, description="Anggota tidak ditemukan.")

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return fail("Nama anggota wajib diisi.", code=422)
    member.name = name
    member.position = (payload.get("position") or "").strip() or None
    member.note = (payload.get("note") or "").strip() or None
    if "photo_file_id" in payload:
        member.photo_file_id = payload.get("photo_file_id") or None
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description=f"Mengubah anggota {name}")
    db.session.commit()
    return ok("Anggota diperbarui.", {"member": member.to_dict()})


@bp.delete("/requests/<int:request_id>/members/<int:member_id>")
@role_required("USER")
def delete_member(request_id, member_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    member = BookMember.query.filter_by(id=member_id, request_id=book_request.id).first()
    if member is None:
        abort(404, description="Anggota tidak ditemukan.")
    db.session.delete(member)
    db.session.flush()
    book_request.member_count = BookMember.query.filter_by(request_id=book_request.id).count()
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description=f"Menghapus anggota {member.name}")
    db.session.commit()
    return ok("Anggota dihapus.")


# --------------------------------------------------------------------------
# texts
# --------------------------------------------------------------------------
@bp.put("/requests/<int:request_id>/texts")
@role_required("USER")
def save_texts(request_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    payload = request.get_json(silent=True) or {}
    sections = payload.get("texts") or {}
    if not isinstance(sections, dict):
        return fail("Format data text tidak valid.", code=422)

    existing = {t.section: t for t in book_request.texts}
    for section, content in sections.items():
        if section not in VALID_SECTIONS:
            return fail(f"Section {section} tidak dikenal.", code=422)
        content = content or ""
        if section in existing:
            existing[section].content = content
        else:
            db.session.add(BookText(request_id=book_request.id, section=section,
                                    content=content))
    audit("UPDATE_REQUEST", user=current_user(), request_obj=book_request,
          description="Memperbarui materi text")
    db.session.commit()
    return ok("Text berhasil disimpan.")


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------
@bp.post("/requests/<int:request_id>/files")
@login_required
def upload_file(request_id):
    book_request = get_request_or_404(request_id)
    user = current_user()
    # Owner uploads materials; PRODUCTION may attach the FINAL result.
    category = (request.form.get("category") or "SUPPORT").upper()
    if user.role_name == "USER":
        ensure_owner_editable(book_request)
        if category == "FINAL":
            abort(403, description="File final hanya dapat diunggah tim produksi.")
    elif user.role_name == "PRODUCTION":
        if category != "FINAL":
            abort(403, description="Tim produksi hanya dapat mengunggah file final.")
    else:
        abort(403, description="Role Anda tidak dapat mengunggah file.")

    if category not in ("COVER", "MEMBER_PHOTO", "DOCUMENTATION", "SUPPORT",
                        "ATTACHMENT", "FINAL"):
        return fail("Kategori file tidak valid.", code=422)

    storage = request.files.get("file")
    if storage is None or not storage.filename:
        return fail("Tidak ada file yang dipilih.", code=422)

    try:
        meta = save_upload(storage, subdir=f"request_{book_request.id}")
    except UploadError as exc:
        return fail(str(exc), code=422)

    book_file = BookFile(request_id=book_request.id, uploaded_by=user.id,
                         category=category, revision_number=book_request.revision_count,
                         **meta)
    db.session.add(book_file)
    audit("UPLOAD_FILE", user=user, request_obj=book_request,
          description=f"Upload {meta['original_filename']} ({category})")
    db.session.commit()
    return ok("File berhasil diunggah.", {"file": book_file.to_dict()}, 201)


@bp.delete("/requests/<int:request_id>/files/<int:file_id>")
@role_required("USER")
def delete_file(request_id, file_id):
    book_request = get_request_or_404(request_id)
    ensure_owner_editable(book_request)
    book_file = BookFile.query.filter_by(id=file_id, request_id=book_request.id).first()
    if book_file is None:
        abort(404, description="File tidak ditemukan.")
    if book_file.uploaded_by != current_user().id:
        abort(403, description="Anda hanya dapat menghapus file milik sendiri.")

    path = os.path.join(os.path.abspath(current_app.config["UPLOAD_FOLDER"]),
                        book_file.file_path)
    BookMember.query.filter_by(photo_file_id=book_file.id).update({"photo_file_id": None})
    audit("DELETE_FILE", user=current_user(), request_obj=book_request,
          description=f"Hapus file {book_file.original_filename}")
    db.session.delete(book_file)
    db.session.commit()
    if os.path.isfile(path):
        os.remove(path)
    return ok("File dihapus.")


@bp.get("/files/<int:file_id>")
@login_required
def download_file(file_id):
    """Serve an upload only to users allowed to see the owning request."""
    book_file = BookFile.query.get(file_id)
    if book_file is None:
        abort(404, description="File tidak ditemukan.")
    ensure_can_view(book_file.request)
    path = resolve_upload_path(book_file.file_path)
    as_attachment = request.args.get("download") == "1" or not book_file.is_image
    return send_file(path, mimetype=book_file.mime_type, as_attachment=as_attachment,
                     download_name=book_file.original_filename)
