from flask import Blueprint, request, redirect, session
from sqlalchemy.orm import Session
import bcrypt as _bcrypt
import os
import random
import time as time_module

from database import get_db
from models import User
from templates import render, get_user_from_session
from config import UPLOAD_DIR

bp = Blueprint("profile", __name__)


def save_profile_image(file):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"profile_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"


@bp.route("/profile")
def profile_page():
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    current_user = db.query(User).filter(User.id == session["user_id"]).first()
    db.close()
    user_dict = get_user_from_session()
    return render("profile.html", user=user_dict, profile=current_user)


@bp.route("/settings")
def settings_page():
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    current_user = db.query(User).filter(User.id == session["user_id"]).first()
    db.close()
    user_dict = get_user_from_session()
    return render("settings.html", user=user_dict, profile=current_user)


@bp.route("/settings", methods=["POST"])
def settings_update():
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    current_user = db.query(User).filter(User.id == session["user_id"]).first()

    current_user.full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    if email:
        existing = db.query(User).filter(User.email == email, User.id != current_user.id).first()
        if not existing:
            current_user.email = email
    current_user.phone = request.form.get("phone", "").strip()
    current_user.website = request.form.get("website", "").strip()
    current_user.bio = request.form.get("bio", "").strip()

    profile_image = request.files.get("profile_image")
    if profile_image and profile_image.filename:
        url = save_profile_image(profile_image)
        current_user.profile_image = url

    new_password = request.form.get("new_password", "")
    if new_password:
        current_password = request.form.get("current_password", "")
        if not current_password:
            db.close()
            return render("settings.html", user=get_user_from_session(), profile=current_user, error="Current password is required")
        if not _bcrypt.checkpw(current_password.encode(), current_user.password_hash.encode()):
            db.close()
            return render("settings.html", user=get_user_from_session(), profile=current_user, error="Current password is incorrect")
        if len(new_password) < 6:
            db.close()
            return render("settings.html", user=get_user_from_session(), profile=current_user, error="New password must be at least 6 characters")
        if new_password != request.form.get("confirm_password", ""):
            db.close()
            return render("settings.html", user=get_user_from_session(), profile=current_user, error="Passwords do not match")
        current_user.password_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt()).decode()

    db.commit()
    session["profile_image"] = current_user.profile_image or ""
    db.close()
    return redirect("/settings?updated=1")
