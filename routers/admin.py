from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from slugify import slugify
import os
import random
import string
import time as time_module
from typing import List

from database import get_db
from models import Product, ProductImage, Category, User, HeroSlide, AffiliateClick, SocialLink, Role, Platform, UserLink
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from routers.auth import get_user_from_token, require_admin
import bcrypt as _bcrypt
from templates import render, invalidate_social_cache

router = APIRouter(prefix="/admin", tags=["admin"])


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_slug(text: str) -> str:
    base = slugify(text)[:200]
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}-{suffix}"


def save_upload(file) -> str:
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"prod_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    content = file.file.read()
    with open(path, "wb") as f:
        f.write(content)
    return f"/static/uploads/{filename}"


def get_user_dict(user):
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    return render("admin/dashboard.html", {
        "request": request,
        "user": get_user_dict(user),
        "total_products": db.query(func.count(Product.id)).scalar() or 0,
        "total_categories": db.query(func.count(Category.id)).scalar() or 0,
        "total_clicks": db.query(func.count(AffiliateClick.id)).scalar() or 0,
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "recent_products": db.query(Product).order_by(desc(Product.created_at)).limit(5).all(),
    })


@router.get("/products")
def admin_products(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    products = db.query(Product).order_by(desc(Product.created_at)).all()
    return render("admin/products.html", {
        "request": request,
        "user": get_user_dict(user),
        "products": products,
    })


@router.get("/products/add")
def admin_add_product_page(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    categories = db.query(Category).order_by(Category.name).all()
    return render("admin/product_form.html", {
        "request": request,
        "user": get_user_dict(user),
        "categories": categories,
        "product": None,
        "edit_mode": False,
    })


@router.post("/products/add")
def admin_add_product(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(""),
    short_description: str = Form(""),
    description: str = Form(""),
    price: str = Form(""),
    old_price: str = Form(""),
    rating: str = Form("0"),
    category_id: str = Form(""),
    affiliate_platform: str = Form("amazon"),
    affiliate_url: str = Form(""),
    is_featured: str = Form(""),
    is_new: str = Form(""),
    image: str = Form(""),
    images: List[UploadFile] = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    title = title.strip()
    if not title:
        categories = db.query(Category).order_by(Category.name).all()
        return render("admin/product_form.html", {
            "request": request, "user": get_user_dict(user), "categories": categories,
            "product": None, "edit_mode": False, "error": "Title is required"
        })

    image_url = image

    slug = gen_slug(title)
    product = Product(
        title=title, slug=slug,
        short_description=short_description,
        description=description,
        image=image_url,
        price=float(price) if price else None,
        old_price=float(old_price) if old_price else None,
        rating=float(rating),
        category_id=int(category_id) if category_id else None,
        affiliate_platform=affiliate_platform,
        affiliate_url=affiliate_url,
        is_featured=is_featured == "on",
        is_new=is_new == "on",
    )
    db.add(product)
    db.flush()

    # Save gallery images from uploaded files
    if images:
        for idx, f in enumerate(images):
            if f.filename and allowed_file(f.filename):
                url = save_upload(f)
                pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
                db.add(pi)
                if not image_url:
                    product.image = url
                    image_url = url

    db.commit()
    return RedirectResponse(url="/admin/products", status_code=302)


@router.get("/products/edit/{pid}")
def admin_edit_product_page(pid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        raise HTTPException(status_code=404)

    # Load images eagerly
    product.images = db.query(ProductImage).filter(ProductImage.product_id == pid).order_by(ProductImage.sort_order).all()

    categories = db.query(Category).order_by(Category.name).all()
    return render("admin/product_form.html", {
        "request": request,
        "user": get_user_dict(user),
        "categories": categories,
        "product": product,
        "edit_mode": True,
    })


@router.post("/products/edit/{pid}")
def admin_edit_product(
    pid: int,
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(""),
    short_description: str = Form(""),
    description: str = Form(""),
    price: str = Form(""),
    old_price: str = Form(""),
    rating: str = Form("0"),
    category_id: str = Form(""),
    affiliate_platform: str = Form("amazon"),
    affiliate_url: str = Form(""),
    is_featured: str = Form(""),
    is_new: str = Form(""),
    image: str = Form(""),
    images: List[UploadFile] = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        raise HTTPException(status_code=404)

    product.title = title or product.title
    product.short_description = short_description or product.short_description
    product.description = description or product.description
    product.price = float(price) if price else None
    product.old_price = float(old_price) if old_price else None
    product.rating = float(rating)
    product.category_id = int(category_id) if category_id else None
    product.affiliate_platform = affiliate_platform or product.affiliate_platform
    product.affiliate_url = affiliate_url or product.affiliate_url
    product.is_featured = is_featured == "on"
    product.is_new = is_new == "on"

    if images:
        for idx, f in enumerate(images):
            if f.filename and allowed_file(f.filename):
                url = save_upload(f)
                pi = ProductImage(product_id=product.id, image_url=url, sort_order=idx)
                db.add(pi)
                if not product.image:
                    product.image = url
    elif image:
        product.image = image

    db.commit()
    return RedirectResponse(url="/admin/products", status_code=302)


@router.get("/products/delete/{pid}")
def admin_delete_product(pid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    product = db.query(Product).filter(Product.id == pid).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/admin/products", status_code=302)


@router.post("/products/images/delete/{img_id}")
def admin_delete_product_image(img_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    img = db.query(ProductImage).filter(ProductImage.id == img_id).first()
    if img:
        pid = img.product_id
        db.delete(img)
        db.commit()
        return RedirectResponse(url=f"/admin/products/edit/{pid}", status_code=302)
    raise HTTPException(status_code=404)


@router.get("/categories")
def admin_categories(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    categories = db.query(Category).order_by(Category.name).all()
    product_counts = {}
    for cat in categories:
        product_counts[cat.id] = db.query(func.count(Product.id)).filter(Product.category_id == cat.id).scalar() or 0

    return render("admin/categories.html", {
        "request": request,
        "user": get_user_dict(user),
        "categories": categories,
        "product_counts": product_counts,
    })


@router.post("/categories/add")
def admin_add_category(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(""),
    description: str = Form(""),
    image: str = Form(""),
    image_file: UploadFile = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    name = name.strip()
    if not name:
        return RedirectResponse(url="/admin/categories", status_code=302)

    slug = slugify(name)[:120]
    if not slug:
        slug = "category-" + "".join(random.choices(string.digits, k=6))

    existing = db.query(Category).filter(Category.slug == slug).first()
    if existing:
        slug = f"{slug}-{random.randint(100,999)}"

    image_url = image
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_upload(image_file)

    cat = Category(name=name, slug=slug, description=description, image=image_url)
    db.add(cat)
    db.commit()
    return RedirectResponse(url="/admin/categories", status_code=302)


@router.post("/categories/edit/{cid}")
def admin_edit_category(
    cid: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(""),
    description: str = Form(""),
    image: str = Form(""),
    image_file: UploadFile = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    cat = db.query(Category).filter(Category.id == cid).first()
    if not cat:
        raise HTTPException(status_code=404)

    cat.name = name or cat.name
    cat.description = description or cat.description

    if image_file and image_file.filename and allowed_file(image_file.filename):
        cat.image = save_upload(image_file)
    elif image:
        cat.image = image

    db.commit()
    return RedirectResponse(url="/admin/categories", status_code=302)


@router.get("/categories/delete/{cid}")
def admin_delete_category(cid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    cat = db.query(Category).filter(Category.id == cid).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse(url="/admin/categories", status_code=302)


@router.get("/clicks")
def admin_clicks(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

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

    return render("admin/clicks.html", {
        "request": request,
        "user": get_user_dict(user),
        "clicks": click_data,
    })


@router.get("/slides")
def admin_slides(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    slides = db.query(HeroSlide).order_by(HeroSlide.sort_order).all()
    return render("admin/slides.html", {
        "request": request,
        "user": get_user_dict(user),
        "slides": slides,
    })


@router.post("/slides/add")
def admin_add_slide(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(""),
    subtitle: str = Form(""),
    image: str = Form(""),
    btn_text: str = Form(""),
    btn_url: str = Form(""),
    btn_type: str = Form("primary"),
    image_file: UploadFile = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    if not title.strip():
        return RedirectResponse(url="/admin/slides", status_code=302)

    image_url = image
    if image_file and image_file.filename and allowed_file(image_file.filename):
        image_url = save_upload(image_file)

    max_order = db.query(func.max(HeroSlide.sort_order)).scalar() or 0
    slide = HeroSlide(
        title=title.strip(),
        subtitle=subtitle.strip(),
        image_url=image_url,
        btn_text=btn_text.strip() or "Shop Now",
        btn_url=btn_url.strip() or "/shop",
        btn_type=btn_type,
        sort_order=max_order + 1,
        is_active=True,
    )
    db.add(slide)
    db.commit()
    return RedirectResponse(url="/admin/slides", status_code=302)


@router.post("/slides/edit/{sid}")
def admin_edit_slide(
    sid: int,
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(""),
    subtitle: str = Form(""),
    image: str = Form(""),
    btn_text: str = Form(""),
    btn_url: str = Form(""),
    btn_type: str = Form("primary"),
    is_active: str = Form(""),
    image_file: UploadFile = File(None),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    slide = db.query(HeroSlide).filter(HeroSlide.id == sid).first()
    if not slide:
        raise HTTPException(status_code=404)

    slide.title = title.strip() or slide.title
    slide.subtitle = subtitle.strip() or slide.subtitle
    slide.btn_text = btn_text.strip() or slide.btn_text
    slide.btn_url = btn_url.strip() or slide.btn_url
    slide.btn_type = btn_type or slide.btn_type
    slide.is_active = is_active == "on"

    if image_file and image_file.filename and allowed_file(image_file.filename):
        slide.image_url = save_upload(image_file)
    elif image:
        slide.image_url = image

    db.commit()
    return RedirectResponse(url="/admin/slides", status_code=302)


@router.get("/slides/delete/{sid}")
def admin_delete_slide(sid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    slide = db.query(HeroSlide).filter(HeroSlide.id == sid).first()
    if slide:
        db.delete(slide)
        db.commit()
    return RedirectResponse(url="/admin/slides", status_code=302)


@router.get("/social-links")
def admin_social_links(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    links = db.query(SocialLink).order_by(SocialLink.sort_order).all()
    return render("admin/social_links.html", {
        "request": request, "user": get_user_dict(user), "links": links,
    })


@router.post("/social-links/add")
def admin_add_social_link(
    request: Request, db: Session = Depends(get_db),
    platform: str = Form(...), url: str = Form(...),
    icon: str = Form("fas fa-link"), sort_order: int = Form(0),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    db.add(SocialLink(platform=platform.strip(), url=url.strip(), icon=icon.strip(), sort_order=sort_order))
    db.commit()
    invalidate_social_cache()
    return RedirectResponse(url="/admin/social-links", status_code=302)


@router.post("/social-links/edit/{lid}")
def admin_edit_social_link(
    lid: int, request: Request, db: Session = Depends(get_db),
    platform: str = Form(...), url: str = Form(...),
    icon: str = Form("fas fa-link"), sort_order: int = Form(0),
    is_active: str = Form(""),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    link = db.query(SocialLink).filter(SocialLink.id == lid).first()
    if not link:
        raise HTTPException(status_code=404)
    link.platform = platform.strip()
    link.url = url.strip()
    link.icon = icon.strip() or "fas fa-link"
    link.sort_order = sort_order
    link.is_active = is_active == "on"
    db.commit()
    invalidate_social_cache()
    return RedirectResponse(url="/admin/social-links", status_code=302)


@router.get("/social-links/delete/{lid}")
def admin_delete_social_link(lid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    link = db.query(SocialLink).filter(SocialLink.id == lid).first()
    if link:
        db.delete(link)
        db.commit()
        invalidate_social_cache()
    return RedirectResponse(url="/admin/social-links", status_code=302)


# ─── Users ────────────────────────────────────────────────
@router.get("/users")
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    users = db.query(User).order_by(User.created_at.desc()).all()
    platforms = db.query(Platform).order_by(Platform.name).all()
    roles_list = db.query(Role).all()
    return render("admin/users.html", {
        "request": request, "user": get_user_dict(user),
        "users": users, "platforms": platforms, "roles_list": roles_list,
    })


@router.post("/users/add")
def admin_add_user(
    request: Request, db: Session = Depends(get_db),
    username: str = Form(...), email: str = Form(...),
    password: str = Form(...), full_name: str = Form(""),
    phone: str = Form(""), website: str = Form(""),
    bio: str = Form(""), role: str = Form("affiliate"),
    is_active: str = Form(""),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing:
        return RedirectResponse(url="/admin/users?error=exists", status_code=302)
    new_user = User(
        username=username, email=email,
        password_hash=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
        full_name=full_name, phone=phone, website=website, bio=bio,
        role=role, is_active=(is_active == "on"),
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/edit/{uid}")
def admin_edit_user(
    uid: int, request: Request, db: Session = Depends(get_db),
    username: str = Form(...), email: str = Form(...),
    full_name: str = Form(""), phone: str = Form(""),
    website: str = Form(""), bio: str = Form(""),
    role: str = Form("affiliate"), password: str = Form(""),
    is_active: str = Form(""), storage_used_mb: float = Form(0),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404)
    target.username = username
    target.email = email
    target.full_name = full_name
    target.phone = phone
    target.website = website
    target.bio = bio
    target.role = role
    target.is_active = (is_active == "on")
    target.storage_used_mb = storage_used_mb
    if password:
        target.password_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@router.get("/users/delete/{uid}")
def admin_delete_user(uid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    target = db.query(User).filter(User.id == uid).first()
    if target and target.id != user.id:
        db.delete(target)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


# ─── Platforms ────────────────────────────────────────────
@router.get("/platforms")
def admin_platforms(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    platforms = db.query(Platform).order_by(Platform.name).all()
    return render("admin/platforms.html", {
        "request": request, "user": get_user_dict(user), "platforms": platforms,
    })


@router.post("/platforms/add")
def admin_add_platform(
    request: Request, db: Session = Depends(get_db),
    name: str = Form(...), icon: str = Form("fas fa-shopping-cart"),
    base_url: str = Form(""), is_active: str = Form(""),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    existing = db.query(Platform).filter(Platform.name == name).first()
    if existing:
        return RedirectResponse(url="/admin/platforms?error=exists", status_code=302)
    db.add(Platform(name=name, icon=icon, base_url=base_url, is_active=(is_active == "on")))
    db.commit()
    return RedirectResponse(url="/admin/platforms", status_code=302)


@router.post("/platforms/edit/{pid}")
def admin_edit_platform(
    pid: int, request: Request, db: Session = Depends(get_db),
    name: str = Form(...), icon: str = Form("fas fa-shopping-cart"),
    base_url: str = Form(""), is_active: str = Form(""),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    plat = db.query(Platform).filter(Platform.id == pid).first()
    if not plat:
        raise HTTPException(status_code=404)
    plat.name = name
    plat.icon = icon
    plat.base_url = base_url
    plat.is_active = (is_active == "on")
    db.commit()
    return RedirectResponse(url="/admin/platforms", status_code=302)


@router.get("/platforms/delete/{pid}")
def admin_delete_platform(pid: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    plat = db.query(Platform).filter(Platform.id == pid).first()
    if plat:
        db.delete(plat)
        db.commit()
    return RedirectResponse(url="/admin/platforms", status_code=302)
