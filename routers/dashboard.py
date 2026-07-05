import os, random, time as time_module
import random as _random
import string as _string
from slugify import slugify
from flask import Blueprint, request, redirect, abort, session
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from database import get_db
from models import User, UserLink, Platform, Product, Category, ProductImage
from templates import render, get_user_from_session
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_slug(text):
    base = slugify(text)[:200]
    suffix = "".join(_random.choices(_string.ascii_lowercase + _string.digits, k=6))
    return f"{base}-{suffix}"


def save_link_image(file):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"link_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"

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
    my_products = db.query(Product).options(joinedload(Product.category)).filter(Product.user_id == current_user_id).order_by(Product.created_at.desc()).all()
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
        my_products=my_products,
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
    image_file = request.files.get("image")
    image_url = ""
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_link_image(image_file)

    link = UserLink(
        user_id=session["user_id"],
        url=url,
        title=request.form.get("title", "").strip() or "Untitled",
        description=request.form.get("description", "").strip(),
        image=image_url,
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

    image_file = request.files.get("image")
    image_field = request.form.get("image_url", "").strip()
    if image_field:
        link.image = image_field
    elif image_file and image_file.filename and allowed_file(image_file.filename):
        link.image = save_link_image(image_file)
    db.commit()
    db.close()
    return redirect("/dashboard?tab=links")


@bp.route("/products/add", methods=["POST"])
def user_add_product():
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    title = request.form.get("title", "").strip()
    if not title:
        db.close()
        return redirect("/dashboard?tab=products&error=title_required")
    slug = gen_slug(title)
    image_field = request.form.get("image", "")
    product = Product(
        title=title, slug=slug,
        short_description=request.form.get("short_description", ""),
        description=request.form.get("description", ""),
        image=image_field,
        price=float(request.form.get("price", 0) or 0) or None,
        old_price=float(request.form.get("old_price", 0) or 0) or None,
        currency=request.form.get("currency", "USD"),
        is_active=True,
        rating=float(request.form.get("rating", 0)),
        category_id=int(request.form.get("category_id") or 0) or None,
        affiliate_platform=request.form.get("affiliate_platform", "amazon"),
        affiliate_url=request.form.get("affiliate_url", ""),
        user_id=session["user_id"],
    )
    image_file = request.files.get("image_file")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        product.image = save_link_image(image_file)
    db.add(product)
    db.flush()
    images = request.files.getlist("images")
    for idx, f in enumerate(images):
        if f.filename and allowed_file(f.filename):
            url = save_link_image(f)
            pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
            db.add(pi)
            if not product.image:
                product.image = url
    db.commit()
    db.close()
    return redirect("/dashboard?tab=products")


@bp.route("/products/edit/<int:pid>", methods=["POST"])
def user_edit_product(pid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    product = db.query(Product).filter(Product.id == pid).first()
    if not product or product.user_id != session["user_id"]:
        db.close()
        abort(403)
    product.title = request.form.get("title", "").strip() or product.title
    product.short_description = request.form.get("short_description", "")
    product.description = request.form.get("description", "")
    product.price = float(request.form.get("price", 0) or 0) or None
    product.old_price = float(request.form.get("old_price", 0) or 0) or None
    product.currency = request.form.get("currency", "USD")
    product.rating = float(request.form.get("rating", 0))
    product.category_id = int(request.form.get("category_id") or 0) or None
    product.affiliate_platform = request.form.get("affiliate_platform", "amazon")
    product.affiliate_url = request.form.get("affiliate_url", "")
    image_field = request.form.get("image", "")
    if image_field:
        product.image = image_field
    image_file = request.files.get("image_file")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        product.image = save_link_image(image_file)
    images = request.files.getlist("images")
    for idx, f in enumerate(images):
        if f.filename and allowed_file(f.filename):
            url = save_link_image(f)
            pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
            db.add(pi)
            if not product.image:
                product.image = url
    db.commit()
    db.close()
    return redirect("/dashboard?tab=products")


@bp.route("/products/delete/<int:pid>")
def user_delete_product(pid):
    if not session.get("user_id"):
        return redirect("/auth/login")
    db = get_db()
    product = db.query(Product).filter(Product.id == pid).first()
    if product and product.user_id == session["user_id"]:
        db.delete(product)
        db.commit()
    db.close()
    return redirect("/dashboard?tab=products")


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


@bp.route("/affiliate/<username>")
def public_affiliate_page(username):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        db.close()
        abort(404)
    links = db.query(UserLink).options(joinedload(UserLink.platform), joinedload(UserLink.category)).filter(
        UserLink.user_id == user.id
    ).order_by(UserLink.created_at.desc()).all()
    categories = db.query(Category).order_by(Category.name).all()
    db.close()
    return render("public_affiliate.html", affiliate_user=user, links=links, categories=categories)


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
