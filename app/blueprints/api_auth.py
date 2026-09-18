from datetime import datetime

from flask import Blueprint, request, session

from . import fail, ok
from ..extensions import db
from ..models import Role, User
from ..security import (csrf_token, current_user, login_required, login_user,
                        logout_user)
from ..services import audit

bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")

DASHBOARD_BY_ROLE = {
    "USER": "/user/dashboard",
    "ADMIN": "/admin/dashboard",
    "EDITOR": "/editor/dashboard",
    "PRODUCTION": "/production/dashboard",
}


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or request.form
    identity = (payload.get("identity") or "").strip()
    password = payload.get("password") or ""
    remember = str(payload.get("remember", "")).lower() in ("1", "true", "on", "yes")

    errors = []
    if not identity:
        errors.append("Username atau email wajib diisi.")
    if not password:
        errors.append("Password wajib diisi.")
    if errors:
        return fail("Data login belum lengkap.", errors, 422)

    user = User.query.filter(
        (User.username == identity) | (User.email == identity.lower())
    ).first()
    if user is None or not user.check_password(password):
        return fail("Username atau password salah.", code=401)
    if not user.is_active:
        return fail("Akun Anda dinonaktifkan. Hubungi administrator.", code=403)

    login_user(user, remember=remember)
    user.last_login_at = datetime.now()
    audit("LOGIN", user=user, description=f"{user.username} login")
    db.session.commit()

    return ok("Login berhasil.", {
        "user": user.to_dict(),
        "redirect": DASHBOARD_BY_ROLE.get(user.role_name, "/"),
        "csrf_token": csrf_token(),
    })


@bp.post("/logout")
@login_required
def logout():
    user = current_user()
    audit("LOGOUT", user=user, description=f"{user.username} logout")
    db.session.commit()
    logout_user()
    return ok("Logout berhasil.", {"redirect": "/"})


@bp.get("/me")
@login_required
def me():
    user = current_user()
    return ok("OK", {"user": user.to_dict(), "csrf_token": csrf_token()})


@bp.put("/me")
@login_required
def update_me():
    """Profile self-service. Role and is_active are deliberately not editable here."""
    user = current_user()
    payload = request.get_json(silent=True) or {}
    full_name = (payload.get("full_name") or "").strip()
    if not full_name:
        return fail("Nama lengkap wajib diisi.", code=422)

    email = (payload.get("email") or "").strip().lower()
    if email and email != user.email:
        if User.query.filter(User.email == email, User.id != user.id).first():
            return fail("Email sudah digunakan.", code=409)
        user.email = email

    user.full_name = full_name
    user.phone = (payload.get("phone") or "").strip() or None

    new_password = payload.get("new_password") or ""
    if new_password:
        if not user.check_password(payload.get("current_password") or ""):
            return fail("Password lama salah.", code=422)
        if len(new_password) < 6:
            return fail("Password baru minimal 6 karakter.", code=422)
        user.set_password(new_password)

    audit("UPDATE_PROFILE", user=user, description="Profil diperbarui")
    db.session.commit()
    return ok("Profil berhasil diperbarui.", {"user": user.to_dict()})
