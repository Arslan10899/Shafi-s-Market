import os, random, time as time_module
from flask import Blueprint, request, redirect, abort, session, jsonify
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from database import get_db
from models import User, Message
from templates import render, get_user_from_session
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS

bp = Blueprint("messages", __name__, url_prefix="/messages")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"msg_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"


@bp.route("")
def inbox():
    if not session.get("user_id"):
        return redirect("/auth/login")
    user_dict = get_user_from_session()
    uid = session["user_id"]
    db = get_db()
    messages = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        Message.receiver_id == uid
    ).order_by(Message.created_at.desc()).all()
    unread_count = db.query(Message).filter(
        Message.receiver_id == uid, Message.is_read == False
    ).count()
    db.close()
    return render("inbox.html",
        user=user_dict,
        messages=messages,
        unread_count=unread_count,
        current_tab="inbox",
    )


@bp.route("/sent")
def sent():
    if not session.get("user_id"):
        return redirect("/auth/login")
    user_dict = get_user_from_session()
    uid = session["user_id"]
    db = get_db()
    messages = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        Message.sender_id == uid
    ).order_by(Message.created_at.desc()).all()
    db.close()
    return render("inbox.html",
        user=user_dict,
        messages=messages,
        unread_count=0,
        current_tab="sent",
    )


@bp.route("/compose")
def compose():
    if not session.get("user_id"):
        return redirect("/auth/login")
    user_dict = get_user_from_session()
    receiver_id = request.args.get("to", type=int)
    receiver = None
    if receiver_id:
        db = get_db()
        receiver = db.query(User).filter(User.id == receiver_id).first()
        db.close()
    return render("compose.html",
        user=user_dict,
        receiver=receiver,
    )


@bp.route("/send", methods=["POST"])
def send():
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    receiver_id = request.form.get("receiver_id", type=int)
    content = request.form.get("content", "").strip()

    if not receiver_id:
        return redirect("/messages/compose?error=receiver_required")
    if not content:
        return redirect(f"/messages/compose?to={receiver_id}&error=content_required")

    db = get_db()
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        db.close()
        return redirect("/messages/compose?error=invalid_receiver")

    image_url = ""
    image_file = request.files.get("image")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_image(image_file)

    msg = Message(
        sender_id=uid,
        receiver_id=receiver_id,
        content=content,
        image=image_url,
    )
    db.add(msg)
    db.commit()
    db.close()
    return redirect("/messages")


@bp.route("/view/<int:mid>")
def view(mid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    user_dict = get_user_from_session()
    uid = session["user_id"]
    db = get_db()
    msg = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(Message.id == mid).first()
    if not msg:
        db.close()
        abort(404)
    if msg.receiver_id != uid and msg.sender_id != uid:
        db.close()
        abort(403)
    if msg.receiver_id == uid and not msg.is_read:
        msg.is_read = True
        db.commit()
    db.close()
    return render("message_view.html",
        user=user_dict,
        msg=msg,
    )


@bp.route("/delete/<int:mid>")
def delete(mid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    db = get_db()
    msg = db.query(Message).filter(Message.id == mid).first()
    if msg and (msg.sender_id == uid or msg.receiver_id == uid):
        db.delete(msg)
        db.commit()
    db.close()
    return redirect(request.referrer or "/messages")


@bp.route("/api/users")
def api_users():
    if not session.get("user_id"):
        return jsonify([])
    q = request.args.get("q", "").strip()
    db = get_db()
    query = db.query(User).filter(User.id != session["user_id"])
    if q:
        query = query.filter(
            or_(User.username.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%"))
        )
    users = query.order_by(User.username).limit(20).all()
    db.close()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name or "",
        "profile_image": u.profile_image or "",
    } for u in users])
