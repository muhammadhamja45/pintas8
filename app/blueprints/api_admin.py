"""Admin API: approval flow, users, book types, audit log."""
from flask import Blueprint, abort, request

from . import fail, ok
from .. import workflow as wf
from ..extensions import db
from ..models import AuditLog, BookRequest, BookType, ProductionOrder, Role, User
from ..security import current_user, role_required
from ..services import (audit, first_user_with_role, new_order_code, notify,
                        notify_role, paginated_payload, production_log,
                        query_requests, transition)

bp = Blueprint("api_admin", __name__, url_prefix="/api/admin")


def get_request_or_404(request_id):
    obj = BookRequest.query.get(request_id)
    if obj is None:
        abort(404, description="Request tidak ditemukan.")
    return obj


def required_note(default_message="Alasan wajib diisi."):
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    return note or None, default_message


# --------------------------------------------------------------------------
# requests
# --------------------------------------------------------------------------
@bp.get("/requests")
@role_required("ADMIN")
def list_requests():
    args = request.args
    pagination = query_requests(
        statuses=args.getlist("status") or None,
        search=args.get("q"),
        book_type_id=args.get("book_type_id", type=int),
        owner_id=args.get("user_id", type=int),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        sort=args.get("sort", "created_at"),
        direction=args.get("direction", "desc"),
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", 10, type=int),
    )
    return ok("OK", paginated_payload(pagination))


@bp.get("/requests/<int:request_id>")
@role_required("ADMIN")
def get_request(request_id):
    return ok("OK", {"request": get_request_or_404(request_id).to_dict(detail=True)})


@bp.post("/requests/<int:request_id>/review")
@role_required("ADMIN")
def start_review(request_id):
    """SUBMITTED -> ADMIN_REVIEW. Claims the request for this admin."""
    book_request = get_request_or_404(request_id)
    admin = current_user()
    try:
        old = transition(book_request, wf.ADMIN_REVIEW, admin,
                         note="Admin mulai memeriksa request", assignee=admin)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)
    audit("START_REVIEW", user=admin, request_obj=book_request, old_status=old,
          new_status=wf.ADMIN_REVIEW, description="Admin mulai review")
    db.session.commit()
    return ok("Review dimulai.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/approve")
@role_required("ADMIN")
def approve(request_id):
    """ADMIN_REVIEW -> ADMIN_APPROVED -> EDITOR_REVIEW, then notify the editors."""
    book_request = get_request_or_404(request_id)
    admin = current_user()
    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None

    try:
        old = transition(book_request, wf.ADMIN_APPROVED, admin,
                         note=note or "Request disetujui admin")
        editor = first_user_with_role("EDITOR")
        transition(book_request, wf.EDITOR_REVIEW, admin,
                   note="Diteruskan ke editor untuk pemeriksaan", assignee=editor)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    notify(book_request.user_id, "Request disetujui Admin",
           f"Request {book_request.request_code} telah disetujui Admin dan "
           "diteruskan ke Editor.", book_request.id, "SUCCESS")
    notify_role("EDITOR", "Request baru menunggu pemeriksaan",
                f"{book_request.request_code} - {book_request.title} siap diperiksa.",
                book_request.id, "INFO")
    audit("APPROVE_REQUEST", user=admin, request_obj=book_request, old_status=old,
          new_status=wf.EDITOR_REVIEW, description=note or "Disetujui admin")
    db.session.commit()
    return ok("Request berhasil disetujui.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/reject")
@role_required("ADMIN")
def reject(request_id):
    book_request = get_request_or_404(request_id)
    admin = current_user()
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return fail("Alasan penolakan wajib diisi.", ["Isi alasan penolakan."], 422)
    try:
        old = transition(book_request, wf.REJECTED, admin, note=note, assignee=None)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)
    notify(book_request.user_id, "Request ditolak",
           f"Request {book_request.request_code} ditolak Admin. Alasan: {note}",
           book_request.id, "DANGER")
    audit("REJECT_REQUEST", user=admin, request_obj=book_request, old_status=old,
          new_status=wf.REJECTED, description=note)
    db.session.commit()
    return ok("Request ditolak.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/return")
@role_required("ADMIN")
def return_to_user(request_id):
    """ADMIN_REVIEW -> DRAFT so the user can fix the submission and resubmit."""
    book_request = get_request_or_404(request_id)
    admin = current_user()
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return fail("Catatan pengembalian wajib diisi.", ["Isi catatan untuk user."], 422)
    try:
        old = transition(book_request, wf.DRAFT, admin, note=note, assignee=None)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)
    book_request.submitted_at = None
    notify(book_request.user_id, "Request dikembalikan Admin",
           f"Request {book_request.request_code} dikembalikan untuk diperbaiki. "
           f"Catatan: {note}", book_request.id, "WARNING")
    audit("RETURN_REQUEST", user=admin, request_obj=book_request, old_status=old,
          new_status=wf.DRAFT, description=note)
    db.session.commit()
    return ok("Request dikembalikan ke user.", {"request": book_request.to_dict()})


@bp.post("/requests/<int:request_id>/send-to-production")
@role_required("ADMIN")
def send_to_production(request_id):
    """READY_FOR_PRODUCTION -> PRODUCTION, creating the production order."""
    book_request = get_request_or_404(request_id)
    admin = current_user()
    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None
    operator = first_user_with_role("PRODUCTION")

    try:
        old = transition(book_request, wf.PRODUCTION, admin,
                         note=note or "Dikirim ke tim produksi", assignee=operator)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    order = book_request.production_order
    if order is None:
        order = ProductionOrder(request_id=book_request.id, order_code=new_order_code(),
                                assigned_to=operator.id if operator else None,
                                status="WAITING", note=note)
        db.session.add(order)
        db.session.flush()
    production_log(order, "QUEUED", admin, new_status="WAITING", note=note)

    notify_role("PRODUCTION", "Buku baru masuk production queue",
                f"{book_request.request_code} - {book_request.title} siap diproduksi.",
                book_request.id, "INFO")
    notify(book_request.user_id, "Request masuk produksi",
           f"Request {book_request.request_code} sedang diproses tim produksi.",
           book_request.id, "INFO")
    audit("SEND_TO_PRODUCTION", user=admin, request_obj=book_request, old_status=old,
          new_status=wf.PRODUCTION, description=note or "Dikirim ke produksi")
    db.session.commit()
    return ok("Request dikirim ke produksi.", {"request": book_request.to_dict(detail=True)})


# --------------------------------------------------------------------------
# users
# --------------------------------------------------------------------------
@bp.get("/users")
@role_required("ADMIN")
def list_users():
    args = request.args
    query = User.query.join(Role)
    search = (args.get("q") or "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(User.full_name.ilike(term) | User.username.ilike(term)
                             | User.email.ilike(term))
    if args.get("role"):
        query = query.filter(Role.name == args.get("role"))
    pagination = query.order_by(User.id).paginate(
        page=args.get("page", 1, type=int),
        per_page=min(args.get("per_page", 10, type=int), 100), error_out=False)
    return ok("OK", {
        "items": [u.to_dict() for u in pagination.items],
        "page": pagination.page, "pages": pagination.pages, "total": pagination.total,
        "has_next": pagination.has_next, "has_prev": pagination.has_prev,
    })


def _validate_user_payload(payload, user=None):
    errors = []
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    full_name = (payload.get("full_name") or "").strip()
    role_name = (payload.get("role") or "").strip().upper()

    if not username:
        errors.append("Username wajib diisi.")
    if not email or "@" not in email:
        errors.append("Email tidak valid.")
    if not full_name:
        errors.append("Nama lengkap wajib diisi.")
    role = Role.query.filter_by(name=role_name).first()
    if role is None:
        errors.append("Role tidak valid.")

    clash = User.query.filter((User.username == username) | (User.email == email))
    if user is not None:
        clash = clash.filter(User.id != user.id)
    if clash.first():
        errors.append("Username atau email sudah digunakan.")
    return errors, username, email, full_name, role


@bp.post("/users")
@role_required("ADMIN")
def create_user():
    payload = request.get_json(silent=True) or {}
    errors, username, email, full_name, role = _validate_user_payload(payload)
    password = payload.get("password") or ""
    if len(password) < 6:
        errors.append("Password minimal 6 karakter.")
    if errors:
        return fail("Data user belum valid.", errors, 422)

    user = User(username=username, email=email, full_name=full_name, role_id=role.id,
                phone=(payload.get("phone") or "").strip() or None,
                is_active=bool(payload.get("is_active", True)))
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    audit("CREATE_USER", user=current_user(), description=f"Membuat user {username}")
    db.session.commit()
    return ok("User berhasil dibuat.", {"user": user.to_dict()}, 201)


@bp.put("/users/<int:user_id>")
@role_required("ADMIN")
def update_user(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404, description="User tidak ditemukan.")
    payload = request.get_json(silent=True) or {}
    errors, username, email, full_name, role = _validate_user_payload(payload, user)
    if errors:
        return fail("Data user belum valid.", errors, 422)

    admin = current_user()
    if user.id == admin.id and role.name != "ADMIN":
        return fail("Anda tidak dapat mengubah role akun sendiri.", code=409)

    user.username, user.email, user.full_name = username, email, full_name
    user.role_id = role.id
    user.phone = (payload.get("phone") or "").strip() or None
    if "is_active" in payload:
        if user.id == admin.id and not payload.get("is_active"):
            return fail("Anda tidak dapat menonaktifkan akun sendiri.", code=409)
        user.is_active = bool(payload.get("is_active"))
    if payload.get("password"):
        if len(payload["password"]) < 6:
            return fail("Password minimal 6 karakter.", code=422)
        user.set_password(payload["password"])

    audit("UPDATE_USER", user=admin, description=f"Memperbarui user {user.username}")
    db.session.commit()
    return ok("User berhasil diperbarui.", {"user": user.to_dict()})


@bp.post("/users/<int:user_id>/toggle")
@role_required("ADMIN")
def toggle_user(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404, description="User tidak ditemukan.")
    admin = current_user()
    if user.id == admin.id:
        return fail("Anda tidak dapat menonaktifkan akun sendiri.", code=409)
    user.is_active = not user.is_active
    state = "diaktifkan" if user.is_active else "dinonaktifkan"
    audit("UPDATE_USER", user=admin, description=f"User {user.username} {state}")
    db.session.commit()
    return ok(f"User {state}.", {"user": user.to_dict()})


# --------------------------------------------------------------------------
# book types
# --------------------------------------------------------------------------
@bp.get("/book-types")
@role_required("ADMIN")
def list_book_types():
    return ok("OK", {"items": [t.to_dict() for t in
                               BookType.query.order_by(BookType.name).all()]})


@bp.post("/book-types")
@role_required("ADMIN")
def create_book_type():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return fail("Nama jenis buku wajib diisi.", code=422)
    if BookType.query.filter(db.func.lower(BookType.name) == name.lower()).first():
        return fail("Jenis buku sudah ada.", code=409)
    book_type = BookType(name=name,
                         description=(payload.get("description") or "").strip() or None,
                         is_active=bool(payload.get("is_active", True)))
    db.session.add(book_type)
    audit("CREATE_BOOK_TYPE", user=current_user(), description=f"Jenis buku {name} dibuat")
    db.session.commit()
    return ok("Jenis buku dibuat.", {"book_type": book_type.to_dict()}, 201)


@bp.put("/book-types/<int:type_id>")
@role_required("ADMIN")
def update_book_type(type_id):
    book_type = BookType.query.get(type_id)
    if book_type is None:
        abort(404, description="Jenis buku tidak ditemukan.")
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return fail("Nama jenis buku wajib diisi.", code=422)
    clash = BookType.query.filter(db.func.lower(BookType.name) == name.lower(),
                                  BookType.id != type_id).first()
    if clash:
        return fail("Jenis buku sudah ada.", code=409)
    book_type.name = name
    book_type.description = (payload.get("description") or "").strip() or None
    if "is_active" in payload:
        book_type.is_active = bool(payload.get("is_active"))
    audit("UPDATE_BOOK_TYPE", user=current_user(), description=f"Jenis buku {name} diubah")
    db.session.commit()
    return ok("Jenis buku diperbarui.", {"book_type": book_type.to_dict()})


@bp.post("/book-types/<int:type_id>/toggle")
@role_required("ADMIN")
def toggle_book_type(type_id):
    book_type = BookType.query.get(type_id)
    if book_type is None:
        abort(404, description="Jenis buku tidak ditemukan.")
    book_type.is_active = not book_type.is_active
    state = "diaktifkan" if book_type.is_active else "dinonaktifkan"
    audit("UPDATE_BOOK_TYPE", user=current_user(),
          description=f"Jenis buku {book_type.name} {state}")
    db.session.commit()
    return ok(f"Jenis buku {state}.", {"book_type": book_type.to_dict()})


# --------------------------------------------------------------------------
# audit log
# --------------------------------------------------------------------------
@bp.get("/audit-logs")
@role_required("ADMIN")
def list_audit_logs():
    args = request.args
    query = AuditLog.query
    if args.get("action"):
        query = query.filter(AuditLog.action == args.get("action"))
    if args.get("user_id", type=int):
        query = query.filter(AuditLog.user_id == args.get("user_id", type=int))
    if args.get("q"):
        query = query.filter(AuditLog.description.ilike(f"%{args.get('q').strip()}%"))
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=args.get("page", 1, type=int),
        per_page=min(args.get("per_page", 20, type=int), 100), error_out=False)
    return ok("OK", {
        "items": [log.to_dict() for log in pagination.items],
        "page": pagination.page, "pages": pagination.pages, "total": pagination.total,
        "has_next": pagination.has_next, "has_prev": pagination.has_prev,
    })
