from flask import Blueprint, request, redirect, abort, session
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from database import get_db
from models import User, UserLink, Platform, Product, Category
from templates import render, get_user_from_session

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("")
def user_dashboard():
    if not session.get("user_id"):
        return redirect("/auth/login")
    current_user_id = session["user_id"]
    user_dict = get_user_from_session()
    tab = request.args.get("tab", "overview")

    db = get_db()
    current_user = db.query(User).filter(User.id == current_user_id).first()
    links = db.query(UserLink).options(joinedload(UserLink.platform), joinedload(UserLink.category)).filter(UserLink.user_id == current_user_id).order_by(UserLink.created_at.desc()).all()
    platforms = db.query(Platform).order_by(Platform.name).all()
    categories = db.query(Category).order_by(Category.name).all()
    products = db.query(Product).options(joinedload(Product.category)).order_by(Product.created_at.desc()).all()
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_categories = db.query(func.count(Category.id)).scalar() or 0
    total_platforms = db.query(func.count(Platform.id)).scalar() or 0
    total_user_links = len(links)
    total_user_clicks = sum(l.clicks_count for l in links)
    db.close()

    return render("user_dashboard.html",
        user=user_dict,
        profile=current_user,
        links=links,
        platforms=platforms,
        categories=categories,
        products=products,
        total_links=total_user_links,
        total_clicks=total_user_clicks,
        total_products=total_products,
        total_categories=total_categories,
        total_platforms=total_platforms,
        current_tab=tab,
    )


@bp.route("/links/add", methods=["POST"])
def add_link():
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    url = request.form.get("url", "").strip()
    if not url:
        db.close()
        return redirect("/dashboard?tab=links&error=url_required")
    link = UserLink(
        user_id=session["user_id"],
        url=url,
        title=request.form.get("title", "").strip() or "Untitled",
        description=request.form.get("description", "").strip(),
        platform_id=int(request.form.get("platform_id", 0)) or None,
        category_id=int(request.form.get("category_id", 0)) or None,
    )
    db.add(link)
    db.commit()
    db.close()
    return redirect("/dashboard?tab=links")


@bp.route("/links/edit/<int:lid>", methods=["POST"])
def edit_link(lid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    link = db.query(UserLink).filter(UserLink.id == lid, UserLink.user_id == session["user_id"]).first()
    if not link:
        db.close()
        abort(404)
    link.title = request.form.get("title", "").strip() or link.title
    link.url = request.form.get("url", "").strip() or link.url
    link.description = request.form.get("description", "").strip()
    link.platform_id = int(request.form.get("platform_id", 0)) or None
    link.category_id = int(request.form.get("category_id", 0)) or None
    db.commit()
    db.close()
    return redirect("/dashboard?tab=links")


@bp.route("/links/delete/<int:lid>")
def delete_link(lid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    link = db.query(UserLink).filter(UserLink.id == lid, UserLink.user_id == session["user_id"]).first()
    if link:
        db.delete(link)
        db.commit()
    db.close()
    return redirect("/dashboard?tab=links")


@bp.route("/go/<int:lid>")
def click_link(lid):
    db = get_db()
    link = db.query(UserLink).filter(UserLink.id == lid).first()
    if not link:
        db.close()
        abort(404)
    link.clicks_count = (link.clicks_count or 0) + 1
    db.commit()
    url = link.url
    db.close()
    return redirect(url)
