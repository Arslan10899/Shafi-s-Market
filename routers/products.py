import random as _random
from flask import Blueprint, request, redirect, abort
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import or_, func

from database import get_db
from models import Product, Category, HeroSlide, AffiliateClick, UserLink, User
from templates import render, get_user_from_session

bp = Blueprint("products", __name__)


def get_categories(db):
    return db.query(Category).order_by(Category.name).all()


@bp.route("/")
def home():
    user = get_user_from_session()
    db = get_db()
    featured = db.query(Product).filter(Product.is_featured == True, Product.is_active == True).all()
    featured_products = _random.sample(featured, min(8, len(featured)))
    new_products = db.query(Product).filter(Product.is_active == True).order_by(Product.created_at.desc()).limit(8).all()
    categories = get_categories(db)
    hero_slides = db.query(HeroSlide).filter(HeroSlide.is_active == True).order_by(HeroSlide.sort_order).all()
    affiliate_links = db.query(UserLink).options(joinedload(UserLink.platform), joinedload(UserLink.user)).order_by(UserLink.created_at.desc()).limit(8).all()
    db.close()

    return render("index.html",
        user=user,
        featured_products=featured_products,
        new_products=new_products,
        categories=categories,
        hero_slides=hero_slides,
        affiliate_links=affiliate_links,
    )


@bp.route("/shop")
def shop():
    user = get_user_from_session()
    category = request.args.get("category")
    search = request.args.get("search", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_rating = request.args.get("min_rating", type=float)
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)
    per_page = 12

    db = get_db()
    q = db.query(Product).options(joinedload(Product.category)).filter(Product.is_active == True)

    if category:
        cat = db.query(Category).filter(Category.slug == category).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)

    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Product.title.ilike(search_term), Product.short_description.ilike(search_term)))

    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)
    if min_rating is not None:
        q = q.filter(Product.rating >= min_rating)

    if sort == "price_asc":
        q = q.order_by(Product.price.asc().nullslast())
    elif sort == "price_desc":
        q = q.order_by(Product.price.desc().nullslast())
    elif sort == "rating":
        q = q.order_by(Product.rating.desc())
    elif sort == "name":
        q = q.order_by(Product.title.asc())
    else:
        q = q.order_by(Product.created_at.desc())

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    products = q.offset((page - 1) * per_page).limit(per_page).all()
    all_categories = get_categories(db)
    selected_category = db.query(Category).filter(Category.slug == category).first() if category else None

    affiliate_links = db.query(UserLink).options(joinedload(UserLink.category), joinedload(UserLink.platform), joinedload(UserLink.user)).filter(
        UserLink.category_id == (selected_category.id if selected_category else None)
    ).order_by(UserLink.created_at.desc()).all() if selected_category else []

    db.close()

    return render("shop.html",
        user=user,
        products=products,
        categories=all_categories,
        selected_category=selected_category,
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        sort=sort,
        page=page,
        total_pages=total_pages,
        total=total,
        affiliate_links=affiliate_links,
    )


@bp.route("/product/<slug>")
def product_detail(slug):
    user = get_user_from_session()
    db = get_db()
    product = db.query(Product).options(joinedload(Product.category), selectinload(Product.images)).filter(Product.slug == slug, Product.is_active == True).first()
    if not product:
        db.close()
        abort(404)

    related_products = db.query(Product).options(joinedload(Product.category)).filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True,
    ).limit(4).all()

    all_categories = get_categories(db)
    db.close()

    return render("product_detail.html",
        user=user,
        product=product,
        related_products=related_products,
        categories=all_categories,
    )


@bp.route("/faq")
def faq_page():
    user = get_user_from_session()
    return render("faq.html", user=user, categories=[])


@bp.route("/privacy")
def privacy_page():
    user = get_user_from_session()
    return render("privacy.html", user=user, categories=[])


@bp.route("/terms")
def terms_page():
    user = get_user_from_session()
    return render("terms.html", user=user, categories=[])


@bp.route("/go/<int:product_id>")
def affiliate_redirect(product_id):
    db = get_db()
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        db.close()
        abort(404)

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")

    click = AffiliateClick(
        product_id=product.id,
        platform=product.affiliate_platform,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent", "")[:300],
    )
    db.add(click)
    url = product.affiliate_url
    db.commit()
    db.close()

    return redirect(url)
