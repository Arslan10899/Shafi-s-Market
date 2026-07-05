from flask import Blueprint, request, redirect, abort, session
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from slugify import slugify
import json
import os
import random
import string
import time as time_module
from datetime import datetime, timedelta

from database import get_db
from models import Product, ProductImage, Category, User, HeroSlide, AffiliateClick, SocialLink, Platform, UserLink, BlogPost, Message, SiteSetting
from config import UPLOAD_DIR, DB_PATH, ALLOWED_EXTENSIONS
from sqlalchemy import create_engine
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

    # Products per category for doughnut chart
    cats = db.query(Category.name, func.count(Product.id)).outerjoin(Product, Product.category_id == Category.id).group_by(Category.id).order_by(Category.name).all()
    cat_labels = [r[0] for r in cats]
    cat_data = [r[1] for r in cats]

    # Clicks per day last 7 days
    today = datetime.utcnow().date()
    click_dates = []
    click_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        cnt = db.query(func.count(AffiliateClick.id)).filter(func.date(AffiliateClick.clicked_at) == day).scalar() or 0
        click_dates.append(day.strftime('%d-%m'))
        click_counts.append(cnt)

    # Featured vs non-featured
    featured_count = db.query(func.count(Product.id)).filter(Product.is_featured == True).scalar() or 0
    new_count = db.query(func.count(Product.id)).filter(Product.is_new == True).scalar() or 0

    ctx = {
        "user": user,
        "total_products": db.query(func.count(Product.id)).scalar() or 0,
        "total_categories": db.query(func.count(Category.id)).scalar() or 0,
        "total_clicks": db.query(func.count(AffiliateClick.id)).scalar() or 0,
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "recent_products": db.query(Product).order_by(desc(Product.created_at)).limit(5).all(),
        "cat_labels": json.dumps(cat_labels),
        "cat_data": json.dumps(cat_data),
        "click_dates": json.dumps(click_dates),
        "click_counts": json.dumps(click_counts),
        "featured_count": featured_count,
        "new_count": new_count,
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

    slug = gen_slug(title)
    product = Product(
        title=title, slug=slug,
        short_description=request.form.get("short_description", ""),
        description=request.form.get("description", ""),
        image="",
        price=float(request.form.get("price", 0) or 0) or None,
        old_price=float(request.form.get("old_price", 0) or 0) or None,
        currency=request.form.get("currency", "USD"),
        is_active=request.form.get("is_active") == "on",
        rating=float(request.form.get("rating", 0)),
        category_id=int(request.form.get("category_id") or 0) or None,
        affiliate_platform=request.form.get("affiliate_platform", "amazon"),
        affiliate_url=request.form.get("affiliate_url", ""),
        is_featured=request.form.get("is_featured") == "on",
        is_new=request.form.get("is_new") == "on",
        user_id=user["id"],
    )
    db.add(product)
    db.flush()

    image_field = request.form.get("image", "")
    images = request.files.getlist("images")

    if image_field:
        product.image = image_field

    for idx, f in enumerate(images):
        if f.filename and allowed_file(f.filename):
            url = save_upload(f)
            pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
            db.add(pi)
            if not product.image:
                product.image = url

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
    product.currency = request.form.get("currency", "USD")
    product.is_active = request.form.get("is_active") == "on"
    product.rating = float(request.form.get("rating", 0))
    product.category_id = int(request.form.get("category_id") or 0) or None
    product.affiliate_platform = request.form.get("affiliate_platform", "") or product.affiliate_platform
    product.affiliate_url = request.form.get("affiliate_url", "") or product.affiliate_url
    product.is_featured = request.form.get("is_featured") == "on"
    product.is_new = request.form.get("is_new") == "on"

    images = request.files.getlist("images")
    image_field = request.form.get("image", "")

    if image_field:
        product.image = image_field
    elif not image_field:
        product.image = ""

    for idx, f in enumerate(images):
        if f.filename and allowed_file(f.filename):
            url = save_upload(f)
            pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
            db.add(pi)
            if not product.image:
                product.image = url

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


@bp.route("/products/images/delete/<int:img_id>")
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


@bp.route("/ceo", methods=["GET", "POST"])
def admin_ceo():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        father = request.form.get("father", "").strip()
        age = request.form.get("age", "").strip()
        address = request.form.get("address", "").strip()
        bio = request.form.get("bio", "").strip()
        image_file = request.files.get("image")

        def set_setting(key, val):
            existing = db.query(SiteSetting).filter(SiteSetting.key == key).first()
            if existing:
                existing.value = val
            else:
                db.add(SiteSetting(key=key, value=val))

        set_setting("ceo_name", name)
        set_setting("ceo_father", father)
        set_setting("ceo_age", age)
        set_setting("ceo_address", address)
        set_setting("ceo_bio", bio)

        if image_file and image_file.filename:
            from config import UPLOAD_DIR
            import random, time as time_module, os
            ext = image_file.filename.rsplit(".", 1)[1].lower() if "." in image_file.filename else "jpg"
            filename = f"ceo_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
            path = os.path.join(UPLOAD_DIR, filename)
            image_file.save(path)
            set_setting("ceo_image", f"/static/uploads/{filename}")

        db.commit()
        db.close()
        return redirect("/admin/ceo?updated=1")

    settings = {r.key: r.value for r in db.query(SiteSetting).all()}
    db.close()
    return render("admin/ceo.html", user=user, settings=settings)


@bp.route("/users")
def admin_users():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    from sqlalchemy import or_
    q = request.args.get("q", "").strip()
    query = db.query(User)
    if q:
        query = query.filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.phone.ilike(f"%{q}%"),
            )
        )
    users = query.options(
        joinedload(User.links), joinedload(User.products)
    ).order_by(User.created_at.desc()).all()
    total = len(users)
    msg_counts = {
        r[0]: r[1]
        for r in db.query(Message.receiver_id, func.count(Message.id)).group_by(Message.receiver_id).all()
    }
    db.close()
    return render("admin/users.html", user=user, users=users, total=total, search=q, msg_counts=msg_counts)


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


@bp.route("/users/block/<int:uid>")
def admin_block_user(uid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    target = db.query(User).filter(User.id == uid).first()
    if target:
        target.is_blocked = True
        db.commit()
    db.close()
    return redirect(request.referrer or "/admin/users")


@bp.route("/users/unblock/<int:uid>")
def admin_unblock_user(uid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    target = db.query(User).filter(User.id == uid).first()
    if target:
        target.is_blocked = False
        db.commit()
    db.close()
    return redirect(request.referrer or "/admin/users")


@bp.route("/conversations")
def admin_conversations():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    from sqlalchemy import or_, and_, func as sa_func

    pairs = db.query(Message.sender_id, Message.receiver_id).distinct().all()
    seen = set()
    conversations = []
    for s, r in pairs:
        if not r:
            continue
        key = (min(s, r), max(s, r))
        if key in seen:
            continue
        seen.add(key)
        u1 = db.query(User).filter(User.id == key[0]).first()
        u2 = db.query(User).filter(User.id == key[1]).first()
        if not u1 or not u2:
            continue
        count = db.query(Message).filter(
            or_(
                and_(Message.sender_id == key[0], Message.receiver_id == key[1]),
                and_(Message.sender_id == key[1], Message.receiver_id == key[0]),
            )
        ).count()
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == key[0], Message.receiver_id == key[1]),
                and_(Message.sender_id == key[1], Message.receiver_id == key[0]),
            )
        ).order_by(Message.created_at.desc()).first()
        conversations.append({
            "user1": u1,
            "user2": u2,
            "count": count,
            "last_message": last_msg,
            "url": f"/admin/conversations/{key[0]}/{key[1]}",
        })
    conversations.sort(key=lambda c: c["last_message"].created_at if c["last_message"] else datetime.min, reverse=True)
    db.close()
    return render("admin/conversations.html", user=user, conversations=conversations)


@bp.route("/conversations/<int:u1>/<int:u2>")
def admin_conversation_view(u1, u2):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    from sqlalchemy import or_, and_
    a = db.query(User).filter(User.id == u1).first()
    b = db.query(User).filter(User.id == u2).first()
    if not a or not b:
        db.close()
        abort(404)
    msgs = db.query(Message).options(
        joinedload(Message.sender), joinedload(Message.receiver)
    ).filter(
        or_(
            and_(Message.sender_id == u1, Message.receiver_id == u2),
            and_(Message.sender_id == u2, Message.receiver_id == u1),
        )
    ).order_by(Message.created_at.asc()).all()
    db.close()
    return render("admin/conversation_view.html", user=user, a=a, b=b, messages=msgs)


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


@bp.route("/backup")
def admin_backup():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    from config import BACKUP_DIR
    saved = []
    if os.path.isdir(BACKUP_DIR):
        for fn in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if fn.endswith(".zip"):
                fpath = os.path.join(BACKUP_DIR, fn)
                stat = os.stat(fpath)
                sz = stat.st_size
                if sz < 1024:
                    size_str = f"{sz} B"
                elif sz < 1024*1024:
                    size_str = f"{sz/1024:.1f} KB"
                else:
                    size_str = f"{sz/1024/1024:.1f} MB"
                saved.append({
                    "name": fn,
                    "size": size_str,
                    "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
                })
    return render("admin/backup.html", user=user, saved_backups=saved)


def _make_backup_zip():
    import zipfile, io
    from database import engine

    db = get_db()
    db.close()
    engine.dispose()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_PATH, arcname="affiliate.db")
        if os.path.isdir(UPLOAD_DIR):
            for root, dirs, files in os.walk(UPLOAD_DIR):
                for fn in files:
                    fpath = os.path.join(root, fn)
                    arcname = os.path.join("uploads", os.path.relpath(fpath, UPLOAD_DIR))
                    zf.write(fpath, arcname=arcname)

    import database as db_mod
    from database import DATABASE_URL
    db_mod.engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

    return buf.getvalue()


def _restore_backup_zip(data):
    import zipfile, io
    from database import engine

    db = get_db()
    db.close()
    engine.dispose()

    zf = zipfile.ZipFile(io.BytesIO(data))
    db_extracted = False
    for name in zf.namelist():
        arcname = name.replace("\\", "/")
        if arcname == "affiliate.db":
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, "wb") as f:
                f.write(zf.read(name))
            db_extracted = True
        elif arcname.startswith("uploads/"):
            rel = arcname[len("uploads/"):]
            if not rel:
                continue
            dest = os.path.join(UPLOAD_DIR, rel)
            if name.endswith("/"):
                os.makedirs(dest, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(zf.read(name))
    zf.close()

    import database as db_mod
    from database import DATABASE_URL
    db_mod.engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

    return db_extracted


@bp.route("/backup/create", methods=["POST"])
def admin_backup_create():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    from config import BACKUP_DIR
    try:
        data = _make_backup_zip()
        fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with open(os.path.join(BACKUP_DIR, fname), "wb") as f:
            f.write(data)
        return redirect("/admin/backup?success=created")
    except Exception as e:
        return redirect(f"/admin/backup?error={str(e)[:50]}")


@bp.route("/backup/saved/restore/<filename>")
def admin_backup_saved_restore(filename):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    from config import BACKUP_DIR
    if ".." in filename or "/" in filename or "\\" in filename:
        return redirect("/admin/backup?error=invalid")
    fpath = os.path.join(BACKUP_DIR, filename)
    if not os.path.isfile(fpath):
        return redirect("/admin/backup?error=File+not+found")
    try:
        with open(fpath, "rb") as f:
            ok = _restore_backup_zip(f.read())
        if not ok:
            return redirect("/admin/backup?error=invalid")
        return redirect("/admin/backup?success=restored")
    except Exception as e:
        return redirect(f"/admin/backup?error={str(e)[:50]}")


@bp.route("/backup/saved/download/<filename>")
def admin_backup_saved_download(filename):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    from config import BACKUP_DIR
    if ".." in filename or "/" in filename or "\\" in filename:
        return redirect("/admin/backup?error=invalid")
    fpath = os.path.join(BACKUP_DIR, filename)
    if not os.path.isfile(fpath):
        return redirect("/admin/backup?error=File+not+found")
    from flask import Response as FlaskResponse
    with open(fpath, "rb") as f:
        data = f.read()
    return FlaskResponse(
        data,
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/backup/saved/delete/<filename>")
def admin_backup_saved_delete(filename):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    from config import BACKUP_DIR
    if ".." in filename or "/" in filename or "\\" in filename:
        return redirect("/admin/backup?error=invalid")
    fpath = os.path.join(BACKUP_DIR, filename)
    if os.path.isfile(fpath):
        os.remove(fpath)
    return redirect("/admin/backup?success=deleted")


@bp.route("/backup/export")
def admin_backup_export():
    user = require_admin()
    if not user:
        return redirect("/auth/login")

    from flask import Response as FlaskResponse

    try:
        data = _make_backup_zip()
        return FlaskResponse(
            data,
            mimetype="application/zip",
            headers={"Content-Disposition": f"attachment; filename=azmart_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"},
        )
    except Exception as e:
        return redirect(f"/admin/backup?error={str(e)[:50]}")


@bp.route("/backup/import", methods=["POST"])
def admin_backup_import():
    user = require_admin()
    if not user:
        return redirect("/auth/login")

    file = request.files.get("backup_file")
    if not file or not file.filename:
        return redirect("/admin/backup?error=nofile")

    if not file.filename.endswith(".zip"):
        return redirect("/admin/backup?error=invalid")

    try:
        ok = _restore_backup_zip(file.read())
        if not ok:
            return redirect("/admin/backup?error=invalid")
        return redirect("/admin/backup?success=restored")
    except Exception as e:
        return redirect(f"/admin/backup?error={str(e)[:50]}")


# ===== BLOG MANAGEMENT =====

@bp.route("/blog")
def admin_blog():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    posts = db.query(BlogPost).order_by(desc(BlogPost.created_at)).all()
    db.close()
    return render("admin/blog.html", user=user, posts=posts)


@bp.route("/blog/add", methods=["GET", "POST"])
def admin_blog_add():
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    if request.method == "GET":
        return render("admin/blog_form.html", user=user, post=None)
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    excerpt = request.form.get("excerpt", "").strip()
    image = request.form.get("image", "").strip()
    author = request.form.get("author", "Admin").strip()
    if not title or not content:
        return redirect("/admin/blog/add?error=required")
    slug = gen_slug(title)
    db = get_db()
    post = BlogPost(title=title, slug=slug, content=content, excerpt=excerpt, image=image, author=author)
    db.add(post)
    db.commit()
    db.close()
    return redirect("/admin/blog?success=added")


@bp.route("/blog/edit/<int:pid>", methods=["GET", "POST"])
def admin_blog_edit(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    post = db.query(BlogPost).filter_by(id=pid).first()
    if not post:
        db.close()
        return redirect("/admin/blog?error=notfound")
    if request.method == "GET":
        return render("admin/blog_form.html", user=user, post=post)
    post.title = request.form.get("title", post.title).strip()
    post.content = request.form.get("content", post.content).strip()
    post.excerpt = request.form.get("excerpt", post.excerpt).strip()
    post.image = request.form.get("image", post.image).strip()
    post.author = request.form.get("author", post.author).strip()
    db.commit()
    db.close()
    return redirect("/admin/blog?success=updated")


@bp.route("/blog/toggle/<int:pid>")
def admin_blog_toggle(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    post = db.query(BlogPost).filter_by(id=pid).first()
    if post:
        post.is_published = not post.is_published
        db.commit()
    db.close()
    return redirect("/admin/blog")


@bp.route("/blog/delete/<int:pid>")
def admin_blog_delete(pid):
    user = require_admin()
    if not user:
        return redirect("/auth/login")
    db = get_db()
    post = db.query(BlogPost).filter_by(id=pid).first()
    if post:
        db.delete(post)
        db.commit()
    db.close()
    return redirect("/admin/blog?success=deleted")
