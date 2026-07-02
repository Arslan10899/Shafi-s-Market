from flask import Blueprint, request, redirect, session, render_template
import bcrypt as _bcrypt
import re

from database import get_db
from models import User
from templates import render, get_user_from_session

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login")
def login_page():
    user = get_user_from_session()
    if user.get("id"):
        return redirect("/")
    return render("login.html")


@bp.route("/register")
def register_page():
    user = get_user_from_session()
    if user.get("id"):
        return redirect("/")
    return render("register.html")


@bp.route("/login", methods=["POST"])
def login():
    user_data = get_user_from_session()
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if not username or not password:
        return render("login.html", error="Username and password are required"), 400

    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if not user or not _bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return render("login.html", error="Invalid username or password"), 400

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session["profile_image"] = user.profile_image or ""
    return redirect("/")


@bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not username or not email or not password:
        return render("register.html", error="All fields are required"), 400
    if len(username) < 3:
        return render("register.html", error="Username must be at least 3 characters"), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return render("register.html", error="Invalid email address"), 400
    if len(password) < 6:
        return render("register.html", error="Password must be at least 6 characters"), 400
    if password != confirm_password:
        return render("register.html", error="Passwords do not match"), 400

    db = get_db()
    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing:
        db.close()
        return render("register.html", error="Username or email already exists"), 400

    user = User(
        username=username,
        email=email,
        password_hash=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session["profile_image"] = user.profile_image or ""
    return redirect("/")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
