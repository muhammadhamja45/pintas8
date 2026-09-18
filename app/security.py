"""Session auth, RBAC decorators, CSRF, and upload validation."""
import functools
import hmac
import mimetypes
import os
import secrets
import uuid

from flask import abort, current_app, g, jsonify, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from .models import User

ALLOWED_EXTENSIONS = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip", "txt": "text/plain",
}


# --------------------------------------------------------------------------
# current user
# --------------------------------------------------------------------------
def load_current_user():
    """Populate g.user from the session. Registered as a before_request hook."""
    g.user = None
    uid = session.get("user_id")
    if uid:
        user = User.query.get(uid)
        if user and user.is_active:
            g.user = user
        else:
            session.clear()


def login_user(user, remember=False):
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role_name
    session.permanent = bool(remember)
    session["csrf_token"] = secrets.token_urlsafe(32)
    g.user = user


def logout_user():
    session.clear()
    g.user = None


def current_user():
    return getattr(g, "user", None)


def wants_json():
    return (request.path.startswith("/api/")
            or request.accept_mimetypes.best == "application/json"
            or request.is_json)


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_protect():
    """Reject unsafe requests without a matching token. before_request hook."""
    if request.method in SAFE_METHODS:
        return None
    sent = (request.headers.get("X-CSRF-Token")
            or request.form.get("csrf_token")
            or (request.get_json(silent=True) or {}).get("csrf_token"))
    expected = session.get("csrf_token")
    if not expected or not sent or not hmac.compare_digest(str(sent), str(expected)):
        abort(400, description="CSRF token tidak valid atau hilang.")
    return None


# --------------------------------------------------------------------------
# RBAC
# --------------------------------------------------------------------------
def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            if wants_json():
                return jsonify(success=False, message="Anda harus login terlebih dahulu.",
                               errors=[]), 401
            return redirect(url_for("auth.login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """Allow only the listed roles. Applied on both API and page routes."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                if wants_json():
                    return jsonify(success=False, message="Anda harus login terlebih dahulu.",
                                   errors=[]), 401
                return redirect(url_for("auth.login", next=request.path))
            if user.role_name not in roles:
                abort(403, description="Anda tidak memiliki akses ke halaman ini.")
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# --------------------------------------------------------------------------
# uploads
# --------------------------------------------------------------------------
class UploadError(Exception):
    pass


def save_upload(storage, subdir="requests"):
    """Validate and store an uploaded file. Returns metadata for book_files.

    Guards extension, MIME agreement, size, filename and path traversal.
    """
    filename = secure_filename(storage.filename or "")
    if not filename or "." not in filename:
        raise UploadError("Nama file tidak valid.")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError(f"Ekstensi .{ext} tidak diizinkan.")

    # Trust neither the browser-declared type nor the extension alone: both
    # must agree with the whitelist before the bytes are written.
    declared = (storage.mimetype or "").lower()
    guessed = mimetypes.guess_type(filename)[0] or ALLOWED_EXTENSIONS[ext]
    expected = ALLOWED_EXTENSIONS[ext]
    if declared and declared not in (expected, guessed) and declared != "application/octet-stream":
        raise UploadError("Tipe file tidak sesuai dengan ekstensinya.")

    stream = storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size <= 0:
        raise UploadError("File kosong.")
    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    if size > max_size:
        raise UploadError(f"Ukuran file melebihi batas {max_size // (1024 * 1024)} MB.")

    root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    target_dir = os.path.abspath(os.path.join(root, secure_filename(subdir)))
    if not target_dir.startswith(root + os.sep) and target_dir != root:
        raise UploadError("Lokasi penyimpanan tidak valid.")
    os.makedirs(target_dir, exist_ok=True)

    stored = f"{uuid.uuid4().hex}.{ext}"
    full_path = os.path.join(target_dir, stored)
    storage.save(full_path)

    return {
        "original_filename": filename,
        "stored_filename": stored,
        "mime_type": expected,
        "file_size": size,
        "file_path": os.path.relpath(full_path, root).replace("\\", "/"),
    }


def resolve_upload_path(relative_path):
    """Resolve a stored relative path, refusing anything outside uploads/."""
    root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    full = os.path.abspath(os.path.join(root, relative_path))
    if full != root and not full.startswith(root + os.sep):
        abort(403, description="Akses file ditolak.")
    if not os.path.isfile(full):
        abort(404, description="File tidak ditemukan.")
    return full
