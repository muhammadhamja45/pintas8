"""Server-rendered dashboard pages. Data itself is fetched by the page JS from /api."""
from flask import Blueprint, abort, render_template

from .. import workflow as wf
from ..models import BookRequest, BookType, ProductionOrder, Role, User
from ..security import current_user, login_required, role_required

bp = Blueprint("dashboard", __name__)


def page(template, title, active, **ctx):
    return render_template(template, page_title=title, active=active, **ctx)


# --------------------------------------------------------------------------
# USER
# --------------------------------------------------------------------------
@bp.get("/user/dashboard")
@role_required("USER")
def user_dashboard():
    return page("dash/user_dashboard.html", "Dashboard", "dashboard")


@bp.get("/user/requests/new")
@role_required("USER")
def user_request_new():
    return page("dash/user_request_form.html", "Request Buku", "request-new",
                book_types=BookType.query.filter_by(is_active=True)
                .order_by(BookType.name).all(), request_id=None)


@bp.get("/user/requests")
@role_required("USER")
def user_requests():
    return page("dash/user_requests.html", "Request Saya", "requests",
                book_types=BookType.query.filter_by(is_active=True).all())


@bp.get("/user/revision")
@role_required("USER")
def user_revision():
    return page("dash/user_revision.html", "Revision", "revision")


# --------------------------------------------------------------------------
# ADMIN
# --------------------------------------------------------------------------
@bp.get("/admin/dashboard")
@role_required("ADMIN")
def admin_dashboard():
    return page("dash/admin_dashboard.html", "Dashboard", "dashboard")


ADMIN_QUEUES = {
    "incoming": ("Incoming Requests", [wf.SUBMITTED]),
    "approval": ("Approval", [wf.ADMIN_REVIEW]),
    "editor-queue": ("Editor Queue", [wf.EDITOR_REVIEW, wf.REVISION_REQUIRED,
                                      wf.USER_REVISION, wf.EDITOR_APPROVED]),
    "production-queue": ("Production Queue", [wf.READY_FOR_PRODUCTION, wf.PRODUCTION,
                                              wf.QUALITY_CHECK]),
    "books": ("All Books", []),
}


@bp.get("/admin/<queue>")
@role_required("ADMIN")
def admin_queue(queue):
    if queue not in ADMIN_QUEUES:
        abort(404, description="Halaman tidak ditemukan.")
    title, statuses = ADMIN_QUEUES[queue]
    return page("dash/admin_requests.html", title, queue, queue=queue,
                statuses=statuses,
                book_types=BookType.query.order_by(BookType.name).all())


@bp.get("/admin/users")
@role_required("ADMIN")
def admin_users():
    return page("dash/admin_users.html", "Users", "users",
                roles=Role.query.order_by(Role.id).all())


@bp.get("/admin/book-types")
@role_required("ADMIN")
def admin_book_types():
    return page("dash/admin_book_types.html", "Book Types", "book-types")


@bp.get("/admin/audit-log")
@role_required("ADMIN")
def admin_audit_log():
    return page("dash/admin_audit.html", "Audit Log", "audit-log")


# --------------------------------------------------------------------------
# EDITOR
# --------------------------------------------------------------------------
@bp.get("/editor/dashboard")
@role_required("EDITOR", "ADMIN")
def editor_dashboard():
    return page("dash/editor_dashboard.html", "Dashboard", "dashboard")


EDITOR_QUEUES = {
    "review-queue": ("Review Queue", [wf.EDITOR_REVIEW]),
    "in-review": ("In Review", [wf.EDITOR_REVIEW]),
    "revision": ("Revision", [wf.REVISION_REQUIRED, wf.USER_REVISION]),
    "ready": ("Ready for Production", [wf.EDITOR_APPROVED, wf.READY_FOR_PRODUCTION]),
}


@bp.get("/editor/<queue>")
@role_required("EDITOR", "ADMIN")
def editor_queue(queue):
    if queue not in EDITOR_QUEUES:
        abort(404, description="Halaman tidak ditemukan.")
    title, statuses = EDITOR_QUEUES[queue]
    return page("dash/editor_requests.html", title, queue, statuses=statuses,
                book_types=BookType.query.order_by(BookType.name).all())


# --------------------------------------------------------------------------
# PRODUCTION
# --------------------------------------------------------------------------
@bp.get("/production/dashboard")
@role_required("PRODUCTION")
def production_dashboard():
    return page("dash/production_dashboard.html", "Dashboard", "dashboard")


PRODUCTION_QUEUES = {
    "queue": ("Production Queue", ["WAITING"]),
    "in-production": ("In Production", ["IN_PRODUCTION"]),
    "quality-check": ("Quality Check", ["QUALITY_CHECK"]),
    "completed": ("Completed", ["COMPLETED"]),
}


@bp.get("/production/<queue>")
@role_required("PRODUCTION")
def production_queue(queue):
    if queue not in PRODUCTION_QUEUES:
        abort(404, description="Halaman tidak ditemukan.")
    title, statuses = PRODUCTION_QUEUES[queue]
    return page("dash/production_orders.html", title, queue, statuses=statuses)


@bp.get("/production/orders/<int:order_id>")
@role_required("PRODUCTION", "ADMIN")
def production_order_detail(order_id):
    order = ProductionOrder.query.get(order_id)
    if order is None:
        abort(404, description="Production order tidak ditemukan.")
    return page("dash/production_detail.html", f"Order {order.order_code}", "queue",
                order=order)


# --------------------------------------------------------------------------
# shared pages
# --------------------------------------------------------------------------
@bp.get("/requests/<int:request_id>")
@login_required
def request_detail(request_id):
    book_request = BookRequest.query.get(request_id)
    if book_request is None:
        abort(404, description="Request tidak ditemukan.")
    user = current_user()
    if user.role_name == "USER" and book_request.user_id != user.id:
        abort(403, description="Anda tidak memiliki akses ke request ini.")
    editable = (user.role_name == "USER" and book_request.user_id == user.id
                and book_request.status in wf.USER_EDITABLE)
    return page("dash/request_detail.html", book_request.request_code, "requests",
                req=book_request, editable=editable,
                book_types=BookType.query.filter_by(is_active=True)
                .order_by(BookType.name).all())


@bp.get("/notifications")
@login_required
def notifications():
    return page("dash/notifications.html", "Notifications", "notifications")


@bp.get("/history")
@login_required
def history():
    return page("dash/history.html", "History", "history")


@bp.get("/profile")
@login_required
def profile():
    return page("dash/profile.html", "Profile", "profile")
