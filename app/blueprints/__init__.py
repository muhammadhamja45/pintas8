"""Blueprints: page routes (public/auth/dashboard) and REST API."""
from flask import jsonify


def ok(message="OK", data=None, code=200):
    return jsonify(success=True, message=message, data=data if data is not None else {}), code


def fail(message, errors=None, code=400):
    return jsonify(success=False, message=message, errors=errors or []), code
