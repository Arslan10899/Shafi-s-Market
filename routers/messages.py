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


def get_conversations(uid):
    db = get_db()
    partner_ids = set()
    for r in db.query(Message.sender_id).filter(Message.receiver_id == uid).distinct().all():
        partner_ids.add(r[0])
    for r in db.query(Message.receiver_id).filter(Message.sender_id == uid).distinct().all():
        if r[0]:
            partner_ids.add(r[0])
    convs = []
    for pid in partner_ids:
        partner = db.query(User).filter(User.id == pid).first()
        if not partner:
            continue
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == uid, Message.receiver_id == pid),
                and_(Message.sender_id == pid, Message.receiver_id == uid),
            )
        ).order_by(Message.created_at.desc()).first()
        unread = db.query(Message).filter(
            Message.sender_id == pid, Message.receiver_id == uid, Message.is_read == False
        ).count()
        status, last_seen_str = user_status(partner)
        convs.append({
            "partner": partner,
            "last_message": last_msg,
            "unread": unread,
            "status": status,
            "last_seen_str": last_seen_str,
        })
    db.close()
    convs.sort(key=lambda c: c["last_message"].created_at if c["last_message"] else datetime.min, reverse=True)
    return convs


@bp.route("")
def inbox():
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    user_dict = get_user_from_session()
    convs = get_conversations(uid)
    unread_count = sum(c["unread"] for c in convs)
    return render("inbox.html",
        user=user_dict,
        conversations=convs,
        unread_count=unread_count,
        current_tab="inbox",
    )


@bp.route("/conversation/<int:pid>")
def conversation(pid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    user_dict = get_user_from_session()
    db = get_db()
    partner = db.query(User).filter(User.id == pid).first()
    if not partner:
        db.close()
        abort(404)
    msgs = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        or_(
            and_(Message.sender_id == uid, Message.receiver_id == pid),
            and_(Message.sender_id == pid, Message.receiver_id == uid),
        )
    ).order_by(Message.created_at.asc()).all()

    for m in msgs:
        if m.receiver_id == uid and not m.is_read:
            m.is_read = True
            m.status = "read"
    db.commit()

    status, last_seen_str = user_status(partner)
    blocked = partner.is_blocked
    db.close()
    return render("conversation.html",
        user=user_dict,
        partner=partner,
        messages=msgs,
        partner_status=status,
        partner_last_seen=last_seen_str,
        partner_blocked=blocked,
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


@bp.route("/drafts")
def drafts():
    if not session.get("user_id"):
        return redirect("/auth/login")
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
            msg = Message(sender_id=uid, receiver_id=receiver_id if receiver_id else None, content=content, status="draft")
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

    if receiver.is_blocked:
        db.close()
        return redirect("/messages/compose?error=blocked")

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
    return redirect(f"/messages/conversation/{receiver_id}")


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
        role = session.get("role")
        if role != "admin":
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
    )


@bp.route("/delete/<int:mid>")
def delete(mid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    role = session.get("role")
    db = get_db()
    msg = db.query(Message).filter(Message.id == mid).first()
    if msg and (msg.sender_id == uid or msg.receiver_id == uid or role == "admin"):
        db.delete(msg)
        db.commit()
    db.close()
    return redirect(request.referrer or "/messages")


@bp.route("/delete/conversation/<int:pid>")
def delete_conversation(pid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    uid = session["user_id"]
    db = get_db()
    from sqlalchemy import or_, and_
    msgs = db.query(Message).filter(
        or_(
            and_(Message.sender_id == uid, Message.receiver_id == pid),
            and_(Message.sender_id == pid, Message.receiver_id == uid),
        )
    ).all()
    for m in msgs:
        db.delete(m)
    db.commit()
    db.close()
    return redirect("/messages")


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
    query = db.query(User).filter(User.id != session["user_id"], User.is_blocked == False)
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
