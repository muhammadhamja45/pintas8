"""Production API: start, quality check, complete."""
from datetime import datetime

from flask import Blueprint, abort, request

from . import fail, ok
from .. import workflow as wf
from ..extensions import db
from ..models import BookRequest, ProductionOrder
from ..security import current_user, role_required
from ..services import audit, notify, notify_role, production_log, transition

bp = Blueprint("api_production", __name__, url_prefix="/api/production")


def get_order_or_404(order_id):
    order = ProductionOrder.query.get(order_id)
    if order is None:
        abort(404, description="Production order tidak ditemukan.")
    return order


@bp.get("/orders")
@role_required("PRODUCTION", "ADMIN")
def list_orders():
    args = request.args
    query = ProductionOrder.query.join(BookRequest)
    statuses = args.getlist("status")
    if statuses:
        query = query.filter(ProductionOrder.status.in_(statuses))
    search = (args.get("q") or "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(ProductionOrder.order_code.ilike(term)
                             | BookRequest.title.ilike(term)
                             | BookRequest.request_code.ilike(term))
    pagination = query.order_by(ProductionOrder.created_at.desc()).paginate(
        page=args.get("page", 1, type=int),
        per_page=min(args.get("per_page", 10, type=int), 100), error_out=False)

    items = []
    for order in pagination.items:
        data = order.to_dict()
        data["request"] = order.request.to_dict()
        items.append(data)
    return ok("OK", {
        "items": items, "page": pagination.page, "pages": pagination.pages,
        "total": pagination.total, "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    })


@bp.get("/orders/<int:order_id>")
@role_required("PRODUCTION", "ADMIN")
def get_order(order_id):
    order = get_order_or_404(order_id)
    data = order.to_dict()
    data["request"] = order.request.to_dict(detail=True)
    return ok("OK", {"order": data})


@bp.post("/orders/<int:order_id>/start")
@role_required("PRODUCTION")
def start(order_id):
    """WAITING -> IN_PRODUCTION. The book request is already at PRODUCTION."""
    order = get_order_or_404(order_id)
    operator = current_user()
    if order.status != "WAITING":
        return fail("Order ini sudah diproses.", code=409)
    if order.request.status != wf.PRODUCTION:
        return fail("Request belum dikirim admin ke produksi.", code=409)

    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None
    order.status = "IN_PRODUCTION"
    order.assigned_to = operator.id
    order.started_at = datetime.now()
    order.note = note or order.note
    production_log(order, "START_PRODUCTION", operator, "WAITING", "IN_PRODUCTION", note)

    notify(order.request.user_id, "Produksi dimulai",
           f"Produksi buku {order.request.request_code} telah dimulai.",
           order.request_id, "INFO")
    audit("START_PRODUCTION", user=operator, request_obj=order.request,
          old_status=wf.PRODUCTION, new_status=wf.PRODUCTION,
          description=note or "Produksi dimulai")
    db.session.commit()
    return ok("Produksi dimulai.", {"order": order.to_dict()})


@bp.post("/orders/<int:order_id>/quality-check")
@role_required("PRODUCTION")
def quality_check(order_id):
    """IN_PRODUCTION -> QUALITY_CHECK on both the order and the request."""
    order = get_order_or_404(order_id)
    operator = current_user()
    if order.status != "IN_PRODUCTION":
        return fail("Order belum dalam proses produksi.", code=409)

    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None
    try:
        old = transition(order.request, wf.QUALITY_CHECK, operator,
                         note=note or "Masuk tahap quality check")
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    order.status = "QUALITY_CHECK"
    order.qc_at = datetime.now()
    production_log(order, "QUALITY_CHECK", operator, "IN_PRODUCTION", "QUALITY_CHECK", note)

    audit("QUALITY_CHECK", user=operator, request_obj=order.request, old_status=old,
          new_status=wf.QUALITY_CHECK, description=note or "Quality check")
    db.session.commit()
    return ok("Quality check dimulai.", {"order": order.to_dict()})


@bp.post("/orders/<int:order_id>/complete")
@role_required("PRODUCTION")
def complete(order_id):
    order = get_order_or_404(order_id)
    operator = current_user()
    if order.status != "QUALITY_CHECK":
        return fail("Order harus melewati quality check sebelum diselesaikan.", code=409)

    note = (request.get_json(silent=True) or {}).get("note", "").strip() or None
    try:
        old = transition(order.request, wf.COMPLETED, operator,
                         note=note or "Produksi selesai", assignee=None)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    order.status = "COMPLETED"
    order.completed_at = datetime.now()
    production_log(order, "COMPLETE_PRODUCTION", operator, "QUALITY_CHECK", "COMPLETED", note)

    notify(order.request.user_id, "Buku selesai diproduksi",
           f"Buku {order.request.request_code} - {order.request.title} telah selesai.",
           order.request_id, "SUCCESS")
    notify_role("ADMIN", "Produksi selesai",
                f"{order.request.request_code} telah selesai diproduksi.",
                order.request_id, "SUCCESS")
    audit("COMPLETE_PRODUCTION", user=operator, request_obj=order.request,
          old_status=old, new_status=wf.COMPLETED, description=note or "Produksi selesai")
    db.session.commit()
    return ok("Produksi diselesaikan.", {"order": order.to_dict()})


@bp.post("/orders/<int:order_id>/reject-qc")
@role_required("PRODUCTION")
def reject_qc(order_id):
    """QC failed: send the order back to the press instead of completing it."""
    order = get_order_or_404(order_id)
    operator = current_user()
    if order.status != "QUALITY_CHECK":
        return fail("Order tidak sedang dalam quality check.", code=409)
    note = (request.get_json(silent=True) or {}).get("note", "").strip()
    if not note:
        return fail("Alasan quality check gagal wajib diisi.", code=422)

    try:
        old = transition(order.request, wf.PRODUCTION, operator, note=note)
    except wf.WorkflowError as exc:
        return fail(str(exc), code=409)

    order.status = "IN_PRODUCTION"
    production_log(order, "QC_FAILED", operator, "QUALITY_CHECK", "IN_PRODUCTION", note)
    audit("QUALITY_CHECK", user=operator, request_obj=order.request, old_status=old,
          new_status=wf.PRODUCTION, description=f"QC gagal: {note}")
    db.session.commit()
    return ok("Order dikembalikan ke proses produksi.", {"order": order.to_dict()})
