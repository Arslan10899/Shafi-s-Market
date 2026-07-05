import os, random, time as time_module
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, abort, session, jsonify
from sqlalchemy import or_, and_
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


def update_last_seen():
    uid = session.get("user_id")
    if uid:
        db = get_db()
        db.query(User).filter(User.id == uid).update({"last_seen": datetime.utcnow()})
        db.commit()
        db.close()


def user_status(user):
    if not user or not user.last_seen:
        return "offline", None
    diff = datetime.utcnow() - user.last_seen
    if diff.total_seconds() < 300:
        return "online", None
    mins = int(diff.total_seconds() / 60)
    hours = int(mins / 60)
    days = int(hours / 24)
    if mins < 60:
        return "offline", f"{mins}m ago"
    elif hours < 24:
        return "offline", f"{hours}h ago"
    else:
        return "offline", f"{days}d ago"


def status_icon(status):
    icons = {"draft": '<i class="fas fa-pen text-secondary" title="Draft"></i>',
             "sent": '<i class="fas fa-check text-muted" title="Sent"></i>',
             "delivered": '<i class="fas fa-check-double text-info" title="Delivered"></i>',
             "read": '<i class="fas fa-check-double text-primary" title="Read"></i>'}
    return icons.get(status, "")


@bp.route("")
def inbox():
    if not session.get("user_id"):
        return redirect("/auth/login")
    update_last_seen()
    user_dict = get_user_from_session()
    uid = session["user_id"]
    db = get_db()
    messages = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        Message.receiver_id == uid, Message.status != "draft"
    ).order_by(Message.created_at.desc()).all()
    unread_count = db.query(Message).filter(
        Message.receiver_id == uid, Message.is_read == False, Message.status != "draft"
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
    update_last_seen()
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


@bp.route("/drafts")
def drafts():
    if not session.get("user_id"):
        return redirect("/auth/login")
    update_last_seen()
    user_dict = get_user_from_session()
    uid = session["user_id"]
    db = get_db()
    messages = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        Message.sender_id == uid, Message.status == "draft"
    ).order_by(Message.created_at.desc()).all()
    db.close()
    return render("inbox.html",
        user=user_dict,
        messages=messages,
        unread_count=0,
        current_tab="drafts",
    )


@bp.route("/compose")
def compose():
    if not session.get("user_id"):
        return redirect("/auth/login")
    update_last_seen()
    user_dict = get_user_from_session()
    receiver_id = request.args.get("to", type=int)
    draft_id = request.args.get("draft", type=int)
    receiver = None
    content = ""
    if receiver_id:
        db = get_db()
        receiver = db.query(User).filter(User.id == receiver_id).first()
        db.close()
    if draft_id:
        db = get_db()
        draft = db.query(Message).filter(
            Message.id == draft_id, Message.sender_id == session["user_id"], Message.status == "draft"
        ).first()
        if draft:
            content = draft.content
            if draft.receiver_id:
                receiver = db.query(User).filter(User.id == draft.receiver_id).first()
        db.close()
    return render("compose.html",
        user=user_dict,
        receiver=receiver,
        content=content,
        draft_id=draft_id,
    )


@bp.route("/send", methods=["POST"])
def send():
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    receiver_id = request.form.get("receiver_id", type=int)
    content = request.form.get("content", "").strip()
    draft_id = request.form.get("draft_id", type=int)
    save_draft = request.form.get("save_draft")

    if not receiver_id and not save_draft:
        return redirect("/messages/compose?error=receiver_required")
    if not content:
        return redirect(f"/messages/compose?to={receiver_id}&error=content_required")

    if save_draft:
        db = get_db()
        if draft_id:
            draft = db.query(Message).filter(
                Message.id == draft_id, Message.sender_id == uid, Message.status == "draft"
            ).first()
            if draft:
                draft.content = content
                draft.receiver_id = receiver_id
                if not receiver_id:
                    draft.receiver_id = None
        else:
            msg = Message(sender_id=uid, receiver_id=receiver_id or 0, content=content, status="draft")
            if not receiver_id:
                msg.receiver_id = None
            db.add(msg)
        db.commit()
        db.close()
        return redirect("/messages/drafts?draft_saved=1")

    if not receiver_id:
        return redirect("/messages/compose?error=receiver_required")

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
        status="sent",
    )
    db.add(msg)
    if draft_id:
        db.query(Message).filter(Message.id == draft_id, Message.sender_id == uid, Message.status == "draft").delete()
    db.commit()
    db.close()
    return redirect("/messages")


@bp.route("/view/<int:mid>")
def view(mid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    update_last_seen()
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
    if msg.receiver_id == uid:
        if not msg.is_read:
            msg.is_read = True
            msg.status = "read"
            db.commit()
        elif msg.status == "delivered":
            msg.status = "read"
            db.commit()
    receiver = msg.sender if msg.receiver_id == uid else msg.receiver
    status, last_seen_str = user_status(receiver)
    db.close()
    return render("message_view.html",
        user=user_dict,
        msg=msg,
        receiver_status=status,
        receiver_last_seen=last_seen_str,
        status_icon=status_icon,
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


@bp.route("/mark-delivered/<int:mid>")
def mark_delivered(mid):
    if not session.get("user_id"):
        return "0"
    uid = session["user_id"]
    db = get_db()
    msg = db.query(Message).filter(Message.id == mid, Message.receiver_id == uid, Message.status == "sent").first()
    if msg:
        msg.status = "delivered"
        db.commit()
        db.close()
        return "1"
    db.close()
    return "0"


@bp.route("/api/unread-count")
def api_unread_count():
    if not session.get("user_id"):
        return jsonify({"count": 0})
    uid = session["user_id"]
    db = get_db()
    count = db.query(Message).filter(
        Message.receiver_id == uid, Message.is_read == False
    ).count()
    db.close()
    return jsonify({"count": count})


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
        "last_seen": u.last_seen.isoformat() if u.last_seen else None,
    } for u in users])
