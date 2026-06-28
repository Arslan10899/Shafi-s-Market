import random as _random
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import get_db
from models import Product, ProductImage, Category, HeroSlide, AffiliateClick
from routers.auth import get_user_from_token
from templates import render

router = APIRouter(tags=["products"])


def get_categories(db: Session):
    return db.query(Category).order_by(Category.name).all()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_token(request)

    featured = db.query(Product).filter(Product.is_featured == True).all()
    featured_products = _random.sample(featured, min(8, len(featured)))
    new_products = db.query(Product).order_by(Product.created_at.desc()).limit(8).all()
    categories = get_categories(db)
    hero_slides = db.query(HeroSlide).filter(HeroSlide.is_active == True).order_by(HeroSlide.sort_order).all()

    return render("index.html", {
        "request": request,
        "user": user,
        "featured_products": featured_products,
        "new_products": new_products,
        "categories": categories,
        "hero_slides": hero_slides,
    })


@router.get("/shop")
def shop(
    request: Request,
    category: str = Query(None),
    search: str = Query(""),
    min_price: float = Query(None),
    max_price: float = Query(None),
    min_rating: float = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    user = get_user_from_token(request)
    per_page = 12

    q = db.query(Product)

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

    return render("shop.html", {
        "request": request,
        "user": user,
        "products": products,
        "categories": all_categories,
        "selected_category": selected_category,
        "search": search,
        "min_price": min_price,
        "max_price": max_price,
        "min_rating": min_rating,
        "sort": sort,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })


@router.get("/product/{slug}")
def product_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_token(request)

    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Eagerly load images
    product.images = db.query(ProductImage).filter(ProductImage.product_id == product.id).order_by(ProductImage.sort_order).all()

    related_products = db.query(Product).filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
    ).limit(4).all()

    all_categories = get_categories(db)
    return render("product_detail.html", {
        "request": request,
        "user": user,
        "product": product,
        "related_products": related_products,
        "categories": all_categories,
    })


@router.get("/faq")
def faq_page(request: Request):
    user = get_user_from_token(request)
    return render("faq.html", {"request": request, "user": user, "categories": []})


@router.get("/privacy")
def privacy_page(request: Request):
    user = get_user_from_token(request)
    return render("privacy.html", {"request": request, "user": user, "categories": []})


@router.get("/terms")
def terms_page(request: Request):
    user = get_user_from_token(request)
    return render("terms.html", {"request": request, "user": user, "categories": []})


@router.get("/go/{product_id}")
def affiliate_redirect(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    ip = ""
    try:
        if request.client:
            ip = request.client.host or ""
    except Exception:
        pass

    click = AffiliateClick(
        product_id=product.id,
        platform=product.affiliate_platform,
        ip_address=ip,
        user_agent=request.headers.get("user-agent", "")[:300],
    )
    db.add(click)
    db.commit()

    return RedirectResponse(url=product.affiliate_url, status_code=302)
