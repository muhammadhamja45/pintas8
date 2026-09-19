import os

from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import db
from .security import csrf_protect, csrf_token, load_current_user, current_user, wants_json


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    app.before_request(load_current_user)
    app.before_request(csrf_protect)

    from .blueprints.public import bp as public_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.dashboard import bp as dashboard_bp
    from .blueprints.api_auth import bp as api_auth_bp
    from .blueprints.api_requests import bp as api_requests_bp
    from .blueprints.api_admin import bp as api_admin_bp
    from .blueprints.api_editor import bp as api_editor_bp
    from .blueprints.api_production import bp as api_production_bp
    from .blueprints.api_misc import bp as api_misc_bp

    for bp in (public_bp, auth_bp, dashboard_bp, api_auth_bp, api_requests_bp,
               api_admin_bp, api_editor_bp, api_production_bp, api_misc_bp):
        app.register_blueprint(bp)

    register_jinja(app)
    register_errors(app)
    return app


def register_jinja(app):
    from . import workflow as wf
    from .models import CHECKLIST_FIELDS, TEXT_SECTIONS
    from .services import unread_count

    @app.context_processor
    def inject_globals():
        user = current_user()
        return {
            "APP_NAME": app.config["APP_NAME"],
            "current_user": user,
            "csrf_token": csrf_token,
            "STATUS_LABELS": wf.STATUS_LABELS,
            "STATUS_TONES": wf.STATUS_TONES,
            "ROLE_LABELS": wf.ROLE_LABELS,
            "ALL_STATUSES": wf.ALL_STATUSES,
            "PUBLIC_ELIGIBLE_STATUSES": wf.PUBLIC_ELIGIBLE_STATUSES,
            "CHECKLIST_FIELDS": CHECKLIST_FIELDS,
            "TEXT_SECTIONS": TEXT_SECTIONS,
            "unread_count": unread_count(user.id) if user else 0,
        }

    @app.template_filter("filesize")
    def filesize(value):
        value = float(value or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GB"


def register_errors(app):
    """JSON for API callers, rendered page otherwise. Same status codes either way."""

    @app.errorhandler(HTTPException)
    def handle_http(error):
        if wants_json():
            return jsonify(success=False, message=error.description, errors=[]), error.code
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        db.session.rollback()
        app.logger.exception("Unhandled error: %s", error)
        message = "Terjadi kesalahan pada server."
        if wants_json():
            return jsonify(success=False, message=message, errors=[]), 500
        return render_template("error.html", code=500, message=message), 500
