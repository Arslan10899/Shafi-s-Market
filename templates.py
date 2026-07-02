from flask import session, render_template as flask_render

_social_cache = None


def _load_social_links():
    global _social_cache
    if _social_cache is not None:
        return _social_cache
    try:
        from database import SessionLocal
        from models import SocialLink
        db = SessionLocal()
        _social_cache = db.query(SocialLink).filter(SocialLink.is_active == True).order_by(SocialLink.sort_order).all()
        db.close()
    except Exception:
        _social_cache = []
    return _social_cache


def invalidate_social_cache():
    global _social_cache
    _social_cache = None


def social_links_context():
    return {"social_links": _load_social_links()}


def render(template_name, **context):
    context.setdefault("user", get_user_from_session())
    return flask_render(template_name, **context)


def get_user_from_session():
    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role", "affiliate"),
        "profile_image": session.get("profile_image", ""),
    } if session.get("user_id") else {}
