from flask import Blueprint, request, abort
from sqlalchemy import desc
from database import get_db
from models import BlogPost, Category
from templates import render, get_user_from_session
from routers.products import get_categories

bp = Blueprint("blog", __name__)


@bp.route("/blog")
def blog_list():
    user = get_user_from_session()
    db = get_db()
    page = request.args.get("page", 1, type=int)
    per_page = 9
    total = db.query(BlogPost).filter(BlogPost.is_published == True).count()
    posts = db.query(BlogPost).filter(BlogPost.is_published == True).order_by(desc(BlogPost.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    categories = get_categories(db)
    db.close()
    return render("blog.html", user=user, posts=posts, page=page, total=total, per_page=per_page, categories=categories)


@bp.route("/blog/<slug>")
def blog_detail(slug):
    user = get_user_from_session()
    db = get_db()
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.is_published == True).first()
    if not post:
        db.close()
        abort(404)
    recent = db.query(BlogPost).filter(BlogPost.is_published == True, BlogPost.id != post.id).order_by(desc(BlogPost.created_at)).limit(4).all()
    categories = get_categories(db)
    db.close()
    return render("blog_detail.html", user=user, post=post, recent=recent, categories=categories)
