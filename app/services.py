"""Service layer: status transitions, notifications, audit logging, queries."""
from datetime import datetime

from flask import request as flask_request
from sqlalchemy import or_

from . import workflow as wf
from .extensions import db
from .models import (AuditLog, BookRequest, Notification, ProductionHistory,
                     ProductionOrder, RequestStatusHistory, Role, User)


def _client_ip():
    try:
        return (flask_request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or flask_request.remote_addr)
    except RuntimeError:  # outside a request context
        return None


def audit(action, user=None, request_obj=None, old_status=None, new_status=None,
          description=None):
    db.session.add(AuditLog(
        user_id=user.id if user else None,
        request_id=request_obj.id if request_obj else None,
        action=action,
        old_status=old_status,
        new_status=new_status,
        description=description,
        ip_address=_client_ip(),
    ))


def notify(user_id, title, message, request_id=None, type_="INFO"):
    db.session.add(Notification(user_id=user_id, request_id=request_id, title=title,
                                message=message, type=type_))


def notify_role(role_name, title, message, request_id=None, type_="INFO"):
    """Notify every active user holding a role (admins, editors, production)."""
    users = (User.query.join(Role).filter(Role.name == role_name, User.is_active.is_(True))
             .all())
    for user in users:
        notify(user.id, title, message, request_id, type_)
    return users


def first_user_with_role(role_name):
    return (User.query.join(Role)
            .filter(Role.name == role_name, User.is_active.is_(True))
            .order_by(User.id)
            .first())


def transition(book_request, new_status, actor, note=None, assignee=None):
    """Apply a status change after validating it against the state machine.

    Raises WorkflowError when the move is not legal for the actor's role.
    """
    old = book_request.status
    role = actor.role_name if actor else None
    if not wf.can_transition(old, new_status, role):
        raise wf.WorkflowError(old, new_status, role)

    book_request.status = new_status
    book_request.updated_at = datetime.now()
    if assignee is not None:
        book_request.current_assignee_id = assignee.id if assignee else None
    if new_status == wf.SUBMITTED and book_request.submitted_at is None:
        book_request.submitted_at = datetime.now()
    if new_status == wf.COMPLETED:
        book_request.completed_at = datetime.now()

    db.session.add(RequestStatusHistory(
        request_id=book_request.id, user_id=actor.id if actor else None,
        old_status=old, new_status=new_status, note=note))
    return old


def next_code(model, column, prefix):
    """Sequential business code, e.g. BR-2026-0007."""
    year = datetime.now().year
    pattern = f"{prefix}-{year}-%"
    last = (db.session.query(column)
            .filter(column.like(pattern))
            .order_by(column.desc())
            .first())
    number = int(last[0].rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}-{year}-{number:04d}"


def new_request_code():
    return next_code(BookRequest, BookRequest.request_code, "BR")


def new_order_code():
    return next_code(ProductionOrder, ProductionOrder.order_code, "PO")


def production_log(order, action, actor, old_status=None, new_status=None, note=None):
    db.session.add(ProductionHistory(
        order_id=order.id, user_id=actor.id if actor else None, action=action,
        old_status=old_status, new_status=new_status, note=note))


# --------------------------------------------------------------------------
# shared list query
# --------------------------------------------------------------------------
SORTABLE = {
    "created_at": BookRequest.created_at,
    "updated_at": BookRequest.updated_at,
    "title": BookRequest.title,
    "status": BookRequest.status,
    "deadline": BookRequest.deadline,
    "request_code": BookRequest.request_code,
}


def query_requests(statuses=None, user_id=None, search=None, book_type_id=None,
                   date_from=None, date_to=None, owner_id=None,
                   sort="created_at", direction="desc", page=1, per_page=10):
    """Server-side filtered/sorted/paginated request list shared by all roles."""
    query = BookRequest.query
    if statuses:
        query = query.filter(BookRequest.status.in_(statuses))
    if user_id:
        query = query.filter(BookRequest.user_id == user_id)
    if owner_id:
        query = query.filter(BookRequest.user_id == owner_id)
    if book_type_id:
        query = query.filter(BookRequest.book_type_id == book_type_id)
    if date_from:
        query = query.filter(BookRequest.created_at >= date_from)
    if date_to:
        query = query.filter(BookRequest.created_at <= f"{date_to} 23:59:59")
    if search:
        term = f"%{search.strip()}%"
        query = query.join(User, BookRequest.user_id == User.id).filter(or_(
            BookRequest.request_code.ilike(term),
            BookRequest.title.ilike(term),
            User.full_name.ilike(term),
            User.username.ilike(term),
        ))

    column = SORTABLE.get(sort, BookRequest.created_at)
    query = query.order_by(column.asc() if direction == "asc" else column.desc())

    per_page = max(1, min(int(per_page or 10), 100))
    return query.paginate(page=max(1, int(page or 1)), per_page=per_page, error_out=False)


def paginated_payload(pagination, detail=False):
    return {
        "items": [item.to_dict(detail=detail) for item in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def status_counts(user_id=None):
    """Counts per status straight from the database (no cached/fake numbers)."""
    query = db.session.query(BookRequest.status, db.func.count(BookRequest.id))
    if user_id:
        query = query.filter(BookRequest.user_id == user_id)
    return dict(query.group_by(BookRequest.status).all())


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()
