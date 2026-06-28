from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import bcrypt as _bcrypt
from jose import jwt
from datetime import datetime, timedelta
import re

from database import get_db
from models import User
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from templates import render

router = APIRouter(prefix="/auth", tags=["auth"])


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_user_from_token(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        return {}
    try:
        payload = decode_token(token.replace("Bearer ", ""))
        return {
            "id": payload.get("sub"),
            "username": payload.get("username"),
            "role": payload.get("role", "affiliate"),
            "profile_image": payload.get("profile_image", ""),
        }
    except Exception:
        return {}


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token.replace("Bearer ", ""))
        user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
        return user
    except Exception:
        return None


def require_admin(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        return None
    return user


@router.get("/login")
def login_page(request: Request):
    user = get_user_from_token(request)
    if user.get("id"):
        return RedirectResponse(url="/", status_code=302)
    return render("login.html", {"request": request, "user": user, "categories": []})


@router.get("/register")
def register_page(request: Request):
    user = get_user_from_token(request)
    if user.get("id"):
        return RedirectResponse(url="/", status_code=302)
    return render("register.html", {"request": request, "user": user, "categories": []})


@router.post("/login")
def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(""),
    password: str = Form(""),
):
    if not username or not password:
        return render("login.html", {
            "request": request, "error": "Username and password are required", "user": {}, "categories": []
        }, status_code=400)

    user = db.query(User).filter(User.username == username).first()

    if not user or not _bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return render("login.html", {
            "request": request, "error": "Invalid username or password", "user": {}, "categories": []
        }, status_code=400)

    token = create_token({"sub": str(user.id), "username": user.username, "role": user.role, "profile_image": user.profile_image or ""})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, samesite="lax")
    return response


@router.post("/register")
def register(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
):
    username = username.strip()
    email = email.strip()

    if not username or not email or not password:
        return render("register.html", {
            "request": request, "error": "All fields are required", "user": {}, "categories": []
        }, status_code=400)

    if len(username) < 3:
        return render("register.html", {
            "request": request, "error": "Username must be at least 3 characters", "user": {}, "categories": []
        }, status_code=400)

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return render("register.html", {
            "request": request, "error": "Invalid email address", "user": {}, "categories": []
        }, status_code=400)

    if len(password) < 6:
        return render("register.html", {
            "request": request, "error": "Password must be at least 6 characters", "user": {}, "categories": []
        }, status_code=400)

    if password != confirm_password:
        return render("register.html", {
            "request": request, "error": "Passwords do not match", "user": {}, "categories": []
        }, status_code=400)

    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing:
        return render("register.html", {
            "request": request, "error": "Username or email already exists", "user": {}, "categories": []
        }, status_code=400)

    user = User(username=username, email=email, password_hash=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode())
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token({"sub": str(user.id), "username": user.username, "role": user.role, "profile_image": user.profile_image or ""})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response
