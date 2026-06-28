from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import bcrypt as _bcrypt
import os
import random
import time as time_module

from database import get_db
from models import User
from routers.auth import create_token
from routers.auth import get_user_from_token, get_current_user
from templates import render
from config import UPLOAD_DIR

router = APIRouter(tags=["profile"])


def save_profile_image(file) -> str:
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"profile_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    content = file.file.read()
    with open(path, "wb") as f:
        f.write(content)
    return f"/static/uploads/{filename}"


@router.get("/profile")
def profile_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    user_dict = get_user_from_token(request)
    return render("profile.html", {
        "request": request, "user": user_dict, "profile": current_user,
    })


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    user_dict = get_user_from_token(request)
    return render("settings.html", {
        "request": request, "user": user_dict, "profile": current_user,
    })


@router.post("/settings")
def settings_update(
    request: Request, db: Session = Depends(get_db),
    full_name: str = Form(""), email: str = Form(""),
    phone: str = Form(""), website: str = Form(""),
    bio: str = Form(""), current_password: str = Form(""),
    new_password: str = Form(""), confirm_password: str = Form(""),
    profile_image: UploadFile = File(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    current_user.full_name = full_name.strip()
    if email.strip():
        existing = db.query(User).filter(User.email == email.strip(), User.id != current_user.id).first()
        if not existing:
            current_user.email = email.strip()
    current_user.phone = phone.strip()
    current_user.website = website.strip()
    current_user.bio = bio.strip()

    if profile_image and profile_image.filename:
        url = save_profile_image(profile_image)
        current_user.profile_image = url

    if new_password:
        if not current_password:
            return render("settings.html", {
                "request": request, "user": get_user_from_token(request),
                "profile": current_user, "error": "Current password is required",
            })
        if not _bcrypt.checkpw(current_password.encode(), current_user.password_hash.encode()):
            return render("settings.html", {
                "request": request, "user": get_user_from_token(request),
                "profile": current_user, "error": "Current password is incorrect",
            })
        if len(new_password) < 6:
            return render("settings.html", {
                "request": request, "user": get_user_from_token(request),
                "profile": current_user, "error": "New password must be at least 6 characters",
            })
        if new_password != confirm_password:
            return render("settings.html", {
                "request": request, "user": get_user_from_token(request),
                "profile": current_user, "error": "Passwords do not match",
            })
        current_user.password_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt()).decode()

    db.commit()

    new_token = create_token({
        "sub": str(current_user.id), "username": current_user.username,
        "role": current_user.role, "profile_image": current_user.profile_image or "",
    })
    response = RedirectResponse(url="/settings?updated=1", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {new_token}", httponly=True, max_age=60*24*7*60, samesite="lax")
    return response
