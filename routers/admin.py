from flask import Blueprint, request, redirect, abort, session
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from slugify import slugify
import os
import random
import string
import time as time_module

from database import get_db
from models import Product, ProductImage, Category, User, HeroSlide, AffiliateClick, SocialLink, Platform, UserLink
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS
import bcrypt as _bcrypt
from templates import render, invalidate_social_cache

bp = Blueprint("admin", __name__, url_prefix="/admin")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_slug(text):
    base = slugify(text)[:200]
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}-{suffix}"


def save_upload(file):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"prod_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"


def require_admin():
    if not session.get("user_id") or session.get("role") != "admin":
        return None
    return {"id": session["user_id"], "username": session["username"], "role": session["role"]}


def get_user_dict(user):
    return {"id": user.id, "username": user.username, "role": user.role}


@bp.route("")
def admin_dashboard():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    ctx = {
        "user": user,
        "total_products": db.query(func.count(Product.id)).scalar() or 0,
        "total_categories": db.query(func.count(Category.id)).scalar() or 0,
        "total_clicks": db.query(func.count(AffiliateClick.id)).scalar() or 0,
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "recent_products": db.query(Product).order_by(desc(Product.created_at)).limit(5).all(),
    }
    db.close()
    return render("admin/dashboard.html", **ctx)


@bp.route("/products")
def admin_products():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    products = db.query(Product).options(joinedload(Product.category)).order_by(desc(Product.created_at)).all()
    db.close()
    return render("admin/products.html", user=user, products=products)


@bp.route("/products/add")
def admin_add_product_page():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    categories = db.query(Category).order_by(Category.name).all()
    db.close()
    return render("admin/product_form.html", user=user, categories=categories, product=None, edit_mode=False)


@bp.route("/products/add", methods=["POST"])
def admin_add_product():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    title = request.form.get("title", "").strip()
    if not title:
        categories = db.query(Category).order_by(Category.name).all()
        db.close()
        return render("admin/product_form.html", user=user, categories=categories, product=None, edit_mode=False, error="Title is required")

    image_url = request.form.get("image", "")
    slug = gen_slug(title)
    product = Product(
        title=title, slug=slug,
        short_description=request.form.get("short_description", ""),
        description=request.form.get("description", ""),
        image=image_url,
        price=float(request.form.get("price", 0) or 0) or None,
        old_price=float(request.form.get("old_price", 0) or 0) or None,
        rating=float(request.form.get("rating", 0)),
        category_id=int(request.form.get("category_id", 0)) or None,
        affiliate_platform=request.form.get("affiliate_platform", "amazon"),
        affiliate_url=request.form.get("affiliate_url", ""),
        is_featured=request.form.get("is_featured") == "on",
        is_new=request.form.get("is_new") == "on",
    )
    db.add(product)
    db.flush()

    images = request.files.getlist("images")
    for idx, f in enumerate(images):
        if f.filename and allowed_file(f.filename):
            url = save_upload(f)
            pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
            db.add(pi)
            if not image_url:
                product.image = url
                image_url = url

    db.commit()
    db.close()
    return redirect("/admin/products")


@bp.route("/products/edit/<int:pid>")
def admin_edit_product_page(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        db.close()
        abort(404)
    product.images = db.query(ProductImage).filter(ProductImage.product_id == pid).order_by(ProductImage.sort_order).all()
    categories = db.query(Category).order_by(Category.name).all()
    db.close()
    return render("admin/product_form.html", user=user, categories=categories, product=product, edit_mode=True)


@bp.route("/products/edit/<int:pid>", methods=["POST"])
def admin_edit_product(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        db.close()
        abort(404)

    product.title = request.form.get("title", "") or product.title
    product.short_description = request.form.get("short_description", "") or product.short_description
    product.description = request.form.get("description", "") or product.description
    product.price = float(request.form.get("price", 0) or 0) or None
    product.old_price = float(request.form.get("old_price", 0) or 0) or None
    product.rating = float(request.form.get("rating", 0))
    product.category_id = int(request.form.get("category_id", 0)) or None
    product.affiliate_platform = request.form.get("affiliate_platform", "") or product.affiliate_platform
    product.affiliate_url = request.form.get("affiliate_url", "") or product.affiliate_url
    product.is_featured = request.form.get("is_featured") == "on"
    product.is_new = request.form.get("is_new") == "on"

    images = request.files.getlist("images")
    image_field = request.form.get("image", "")

    if images:
        for idx, f in enumerate(images):
            if f.filename and allowed_file(f.filename):
                url = save_upload(f)
                pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
                db.add(pi)
                if not product.image:
                    product.image = url
    elif image_field:
        product.image = image_field

    db.commit()
    db.close()
    return redirect("/admin/products")


@bp.route("/products/delete/<int:pid>")
def admin_delete_product(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    product = db.query(Product).filter(Product.id == pid).first()
    if product:
        db.delete(product)
        db.commit()
    db.close()
    return redirect("/admin/products")


@bp.route("/products/images/delete/<int:img_id>", methods=["POST"])
def admin_delete_product_image(img_id):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    img = db.query(ProductImage).filter(ProductImage.id == img_id).first()
    if img:
        pid = img.product_id
        db.delete(img)
        db.commit()
        db.close()
        return redirect(f"/admin/products/edit/{pid}")
    db.close()
    abort(404)


@bp.route("/categories")
def admin_categories():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    categories = db.query(Category).order_by(Category.name).all()
    product_counts = {}
    for cat in categories:
        product_counts[cat.id] = db.query(func.count(Product.id)).filter(Product.category_id == cat.id).scalar() or 0
    db.close()
    return render("admin/categories.html", user=user, categories=categories, product_counts=product_counts)


@bp.route("/categories/add", methods=["POST"])
def admin_add_category():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    name = request.form.get("name", "").strip()
    if not name:
        db.close()
        return redirect("/admin/categories")
    slug = slugify(name)[:120]
    if not slug:
        slug = "category-" + "".join(random.choices(string.digits, k=6))
    existing = db.query(Category).filter(Category.slug == slug).first()
    if existing:
        slug = f"{slug}-{random.randint(100,999)}"
    image_url = request.form.get("image", "")
    image_file = request.files.get("image_file")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_upload(image_file)
    cat = Category(name=name, slug=slug, description=request.form.get("description", ""), image=image_url)
    db.add(cat)
    db.commit()
    db.close()
    return redirect("/admin/categories")


@bp.route("/categories/edit/<int:cid>", methods=["POST"])
def admin_edit_category(cid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    cat = db.query(Category).filter(Category.id == cid).first()
    if not cat:
        db.close()
        abort(404)
    cat.name = request.form.get("name", "") or cat.name
    cat.description = request.form.get("description", "") or cat.description
    image_file = request.files.get("image_file")
    image = request.form.get("image", "")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        cat.image = save_upload(image_file)
    elif image:
        cat.image = image
    db.commit()
    db.close()
    return redirect("/admin/categories")


@bp.route("/categories/delete/<int:cid>")
def admin_delete_category(cid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    cat = db.query(Category).filter(Category.id == cid).first()
    if cat:
        db.delete(cat)
        db.commit()
    db.close()
    return redirect("/admin/categories")


@bp.route("/clicks")
def admin_clicks():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    clicks = db.query(AffiliateClick).order_by(desc(AffiliateClick.clicked_at)).limit(100).all()
    click_data = []
    for click in clicks:
        prod = db.query(Product).filter(Product.id == click.product_id).first()
        click_data.append({
            "id": click.id,
            "product_title": prod.title if prod else "Deleted",
            "platform": click.platform,
            "clicked_at": click.clicked_at,
            "ip_address": click.ip_address,
        })
    db.close()
    return render("admin/clicks.html", user=user, clicks=click_data)


@bp.route("/slides")
def admin_slides():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    slides = db.query(HeroSlide).order_by(HeroSlide.sort_order).all()
    db.close()
    return render("admin/slides.html", user=user, slides=slides)


@bp.route("/slides/add", methods=["POST"])
def admin_add_slide():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    title = request.form.get("title", "").strip()
    if not title:
        db.close()
        return redirect("/admin/slides")
    image_url = request.form.get("image", "")
    image_file = request.files.get("image_file")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_upload(image_file)
    max_order = db.query(func.max(HeroSlide.sort_order)).scalar() or 0
    slide = HeroSlide(
        title=title,
        subtitle=request.form.get("subtitle", "").strip(),
        image_url=image_url,
        btn_text=request.form.get("btn_text", "").strip() or "Shop Now",
        btn_url=request.form.get("btn_url", "").strip() or "/shop",
        btn_type=request.form.get("btn_type", "primary"),
        sort_order=max_order + 1,
        is_active=True,
    )
    db.add(slide)
    db.commit()
    db.close()
    return redirect("/admin/slides")


@bp.route("/slides/edit/<int:sid>", methods=["POST"])
def admin_edit_slide(sid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    slide = db.query(HeroSlide).filter(HeroSlide.id == sid).first()
    if not slide:
        db.close()
        abort(404)
    slide.title = request.form.get("title", "").strip() or slide.title
    slide.subtitle = request.form.get("subtitle", "").strip() or slide.subtitle
    slide.btn_text = request.form.get("btn_text", "").strip() or slide.btn_text
    slide.btn_url = request.form.get("btn_url", "").strip() or slide.btn_url
    slide.btn_type = request.form.get("btn_type", "") or slide.btn_type
    slide.is_active = request.form.get("is_active") == "on"
    image_file = request.files.get("image_file")
    image = request.form.get("image", "")
    if image_file and image_file.filename and allowed_file(image_file.filename):
        slide.image_url = save_upload(image_file)
    elif image:
        slide.image_url = image
    db.commit()
    db.close()
    return redirect("/admin/slides")


@bp.route("/slides/delete/<int:sid>")
def admin_delete_slide(sid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    slide = db.query(HeroSlide).filter(HeroSlide.id == sid).first()
    if slide:
        db.delete(slide)
        db.commit()
    db.close()
    return redirect("/admin/slides")


@bp.route("/social-links")
def admin_social_links():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    links = db.query(SocialLink).order_by(SocialLink.sort_order).all()
    db.close()
    return render("admin/social_links.html", user=user, links=links)


@bp.route("/social-links/add", methods=["POST"])
def admin_add_social_link():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    db.add(SocialLink(
        platform=request.form.get("platform", "").strip(),
        url=request.form.get("url", "").strip(),
        icon=request.form.get("icon", "fas fa-link").strip(),
        sort_order=int(request.form.get("sort_order", 0)),
    ))
    db.commit()
    db.close()
    invalidate_social_cache()
    return redirect("/admin/social-links")


@bp.route("/social-links/edit/<int:lid>", methods=["POST"])
def admin_edit_social_link(lid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    link = db.query(SocialLink).filter(SocialLink.id == lid).first()
    if not link:
        db.close()
        abort(404)
    link.platform = request.form.get("platform", "").strip()
    link.url = request.form.get("url", "").strip()
    link.icon = request.form.get("icon", "fas fa-link").strip()
    link.sort_order = int(request.form.get("sort_order", 0))
    link.is_active = request.form.get("is_active") == "on"
    db.commit()
    db.close()
    invalidate_social_cache()
    return redirect("/admin/social-links")


@bp.route("/social-links/delete/<int:lid>")
def admin_delete_social_link(lid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    link = db.query(SocialLink).filter(SocialLink.id == lid).first()
    if link:
        db.delete(link)
        db.commit()
        invalidate_social_cache()
    db.close()
    return redirect("/admin/social-links")


@bp.route("/users")
def admin_users():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    users = db.query(User).options(joinedload(User.links)).order_by(User.created_at.desc()).all()
    db.close()
    return render("admin/users.html", user=user, users=users)


@bp.route("/users/add", methods=["POST"])
def admin_add_user():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    username = request.form.get("username", "")
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing:
        db.close()
        return redirect("/admin/users?error=exists")
    new_user = User(
        username=username, email=email,
        password_hash=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
        full_name=request.form.get("full_name", ""),
        phone=request.form.get("phone", ""),
        website=request.form.get("website", ""),
        bio=request.form.get("bio", ""),
        role=request.form.get("role", "affiliate"),
        is_active=(request.form.get("is_active") == "on"),
    )
    db.add(new_user)
    db.commit()
    db.close()
    return redirect("/admin/users")


@bp.route("/users/edit/<int:uid>", methods=["POST"])
def admin_edit_user(uid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    target = db.query(User).filter(User.id == uid).first()
    if not target:
        db.close()
        abort(404)
    target.username = request.form.get("username", "")
    target.email = request.form.get("email", "")
    target.full_name = request.form.get("full_name", "")
    target.phone = request.form.get("phone", "")
    target.website = request.form.get("website", "")
    target.bio = request.form.get("bio", "")
    target.role = request.form.get("role", "affiliate")
    target.is_active = (request.form.get("is_active") == "on")
    target.storage_used_mb = float(request.form.get("storage_used_mb", 0))
    password = request.form.get("password", "")
    if password:
        target.password_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    db.commit()
    db.close()
    return redirect("/admin/users")


@bp.route("/users/delete/<int:uid>")
def admin_delete_user(uid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    target = db.query(User).filter(User.id == uid).first()
    if target and target.id != user["id"]:
        db.delete(target)
        db.commit()
    db.close()
    return redirect("/admin/users")


@bp.route("/platforms")
def admin_platforms():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    platforms = db.query(Platform).order_by(Platform.name).all()
    db.close()
    return render("admin/platforms.html", user=user, platforms=platforms)


@bp.route("/platforms/add", methods=["POST"])
def admin_add_platform():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    name = request.form.get("name", "")
    existing = db.query(Platform).filter(Platform.name == name).first()
    if existing:
        db.close()
        return redirect("/admin/platforms?error=exists")
    db.add(Platform(
        name=name,
        icon=request.form.get("icon", "fas fa-shopping-cart"),
        base_url=request.form.get("base_url", ""),
        is_active=(request.form.get("is_active") == "on"),
    ))
    db.commit()
    db.close()
    return redirect("/admin/platforms")


@bp.route("/platforms/edit/<int:pid>", methods=["POST"])
def admin_edit_platform(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    plat = db.query(Platform).filter(Platform.id == pid).first()
    if not plat:
        db.close()
        abort(404)
    plat.name = request.form.get("name", "")
    plat.icon = request.form.get("icon", "fas fa-shopping-cart")
    plat.base_url = request.form.get("base_url", "")
    plat.is_active = (request.form.get("is_active") == "on")
    db.commit()
    db.close()
    return redirect("/admin/platforms")


@bp.route("/platforms/delete/<int:pid>")
def admin_delete_platform(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    plat = db.query(Platform).filter(Platform.id == pid).first()
    if plat:
        db.delete(plat)
        db.commit()
    db.close()
    return redirect("/admin/platforms")
