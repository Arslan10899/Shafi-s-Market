import secrets
from functools import wraps
from flask import session, request, abort, render_template


def generate_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_token():
    token = request.form.get("csrf_token")
    return token and session.get("csrf_token") and secrets.compare_digest(token, session["csrf_token"])


def csrf_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == "POST" and not validate_token():
            abort(400, "CSRF validation failed")
        return f(*args, **kwargs)
    return wrapper


def inject_csrf():
    return {"csrf_token": generate_token()}
