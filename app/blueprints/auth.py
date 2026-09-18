from flask import Blueprint, redirect, render_template, request, url_for

from ..extensions import db
from ..security import current_user, logout_user
from ..services import audit
from .api_auth import DASHBOARD_BY_ROLE

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    user = current_user()
    if user:
        return redirect(DASHBOARD_BY_ROLE.get(user.role_name, "/"))
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.post("/logout")
def logout():
    """Form logout for the sidebar. POST-only so it cannot be triggered cross-site;
    csrf_protect already validated the token before this runs."""
    user = current_user()
    if user:
        audit("LOGOUT", user=user, description=f"{user.username} logout")
        db.session.commit()
    logout_user()
    return redirect(url_for("public.home"))


@bp.get("/dashboard")
def dashboard_redirect():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    return redirect(DASHBOARD_BY_ROLE.get(user.role_name, "/"))
