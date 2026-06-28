import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.templating import _TemplateResponse

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=200,
)

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


def render(name: str, context: dict, status_code: int = 200):
    if "request" not in context:
        raise ValueError("context must include a 'request' key")
    if "social_links" not in context:
        context["social_links"] = _load_social_links()
    template = _env.get_template(name)
    return _TemplateResponse(
        template,
        context,
        status_code=status_code,
    )


def get_template(name: str):
    return _env.get_template(name)
