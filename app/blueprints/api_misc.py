"""Notifications, dashboard stats, history, and lookup lists."""
from flask import Blueprint, abort, request

from . import ok
from .. import workflow as wf
from ..extensions import db
from ..models import (BookRequest, BookType, Notification, ProductionOrder,
                      RequestStatusHistory)
from ..security import current_user, login_required, role_required
from ..services import status_counts, unread_count

bp = Blueprint("api_misc", __name__, url_prefix="/api")


# --------------------------------------------------------------------------
# notifications
# --------------------------------------------------------------------------
@bp.get("/notifications")
@login_required
def list_notifications():
    user = current_user()
    query = Notification.query.filter_by(user_id=user.id)
    if request.args.get("unread") == "1":
        query = query.filter_by(is_read=False)
    pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=min(request.args.get("per_page", 10, type=int), 50), error_out=False)
    return ok("OK", {
        "items": [n.to_dict() for n in pagination.items],
        "unread": unread_count(user.id),
        "page": pagination.page, "pages": pagination.pages, "total": pagination.total,
        "has_next": pagination.has_next, "has_prev": pagination.has_prev,
    })


@bp.post("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    user = current_user()
    notification = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if notification is None:
        abort(404, description="Notifikasi tidak ditemukan.")
    notification.is_read = True
    db.session.commit()
    return ok("Notifikasi ditandai dibaca.", {"unread": unread_count(user.id)})


@bp.post("/notifications/read-all")
@login_required
def read_all_notifications():
    user = current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return ok("Semua notifikasi ditandai dibaca.", {"unread": 0})


# --------------------------------------------------------------------------
# lookups
# --------------------------------------------------------------------------
@bp.get("/book-types")
@login_required
def active_book_types():
    types = BookType.query.filter_by(is_active=True).order_by(BookType.name).all()
    return ok("OK", {"items": [t.to_dict() for t in types]})


# --------------------------------------------------------------------------
# history
# --------------------------------------------------------------------------
@bp.get("/history")
@login_required
def history():
    """Status timeline. Users see only their own requests; staff see everything."""
    user = current_user()
    query = RequestStatusHistory.query.join(BookRequest)
    if user.role_name == "USER":
        query = query.filter(BookRequest.user_id == user.id)
    if request.args.get("request_id", type=int):
        query = query.filter(RequestStatusHistory.request_id ==
                             request.args.get("request_id", type=int))
    search = (request.args.get("q") or "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(BookRequest.title.ilike(term)
                             | BookRequest.request_code.ilike(term))
    pagination = query.order_by(RequestStatusHistory.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=min(request.args.get("per_page", 20, type=int), 100), error_out=False)
    return ok("OK", {
        "items": [h.to_dict() for h in pagination.items],
        "page": pagination.page, "pages": pagination.pages, "total": pagination.total,
        "has_next": pagination.has_next, "has_prev": pagination.has_prev,
    })


# --------------------------------------------------------------------------
# dashboard stats (always counted from the database)
# --------------------------------------------------------------------------
@bp.get("/stats")
@login_required
def stats():
    user = current_user()
    role = user.role_name
    counts = status_counts(user_id=user.id if role == "USER" else None)
    total = sum(counts.values())

    def group(*statuses):
        return sum(counts.get(s, 0) for s in statuses)

    if role == "USER":
        cards = {
            "total": total,
            "pending": group(wf.SUBMITTED, wf.ADMIN_REVIEW, wf.ADMIN_APPROVED),
            "revision": group(wf.REVISION_REQUIRED, wf.USER_REVISION),
            "in_progress": group(wf.EDITOR_REVIEW, wf.EDITOR_APPROVED,
                                 wf.READY_FOR_PRODUCTION, wf.PRODUCTION, wf.QUALITY_CHECK),
            "completed": group(wf.COMPLETED),
            "draft": group(wf.DRAFT),
        }
    elif role == "ADMIN":
        cards = {
            "total": total,
            "incoming": group(wf.SUBMITTED),
            "in_review": group(wf.ADMIN_REVIEW),
            "editor_queue": group(wf.EDITOR_REVIEW, wf.REVISION_REQUIRED, wf.USER_REVISION),
            "production_queue": group(wf.READY_FOR_PRODUCTION),
            "in_production": group(wf.PRODUCTION, wf.QUALITY_CHECK),
            "completed": group(wf.COMPLETED),
            "rejected": group(wf.REJECTED, wf.CANCELLED),
        }
    elif role == "EDITOR":
        cards = {
            "review_queue": group(wf.EDITOR_REVIEW),
            "revision": group(wf.REVISION_REQUIRED, wf.USER_REVISION),
            "ready": group(wf.EDITOR_APPROVED, wf.READY_FOR_PRODUCTION),
            "completed": group(wf.COMPLETED),
        }
    else:  # PRODUCTION
        order_counts = dict(db.session.query(
            ProductionOrder.status, db.func.count(ProductionOrder.id))
            .group_by(ProductionOrder.status).all())
        cards = {
            "waiting": order_counts.get("WAITING", 0),
            "in_production": order_counts.get("IN_PRODUCTION", 0),
            "quality_check": order_counts.get("QUALITY_CHECK", 0),
            "completed": order_counts.get("COMPLETED", 0),
        }

    return ok("OK", {"cards": cards, "by_status": counts, "unread": unread_count(user.id)})
