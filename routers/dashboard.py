from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, UserLink, Platform, Product, Category, AffiliateClick
from routers.auth import get_user_from_token, get_current_user
from templates import render

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def user_dashboard(
    request: Request,
    tab: str = Query("overview"),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    user_dict = get_user_from_token(request)
    links = db.query(UserLink).filter(UserLink.user_id == current_user.id).order_by(UserLink.created_at.desc()).all()
    platforms = db.query(Platform).order_by(Platform.name).all()
    categories = db.query(Category).order_by(Category.name).all()
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_categories = db.query(func.count(Category.id)).scalar() or 0
    total_platforms = db.query(func.count(Platform.id)).scalar() or 0
    total_user_links = len(links)
    total_user_clicks = sum(l.clicks_count for l in links)

    ctx = {
        "request": request,
        "user": user_dict,
        "profile": current_user,
        "links": links,
        "platforms": platforms,
        "categories": categories,
        "products": products,
        "total_links": total_user_links,
        "total_clicks": total_user_clicks,
        "total_products": total_products,
        "total_categories": total_categories,
        "total_platforms": total_platforms,
        "current_tab": tab,
    }
    return render("user_dashboard.html", ctx)


@router.post("/links/add")
def add_link(
    request: Request, db: Session = Depends(get_db),
    title: str = Form(""), url: str = Form(""),
    description: str = Form(""), platform_id: int = Form(0),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if not url.strip():
        return RedirectResponse(url="/dashboard?tab=links&error=url_required", status_code=302)
    link = UserLink(
        user_id=current_user.id,
        url=url.strip(),
        title=title.strip() or "Untitled",
        description=description.strip(),
        platform_id=platform_id if platform_id > 0 else None,
    )
    db.add(link)
    db.commit()
    return RedirectResponse(url="/dashboard?tab=links", status_code=302)


@router.post("/links/edit/{lid}")
def edit_link(
    lid: int, request: Request, db: Session = Depends(get_db),
    title: str = Form(""), url: str = Form(""),
    description: str = Form(""), platform_id: int = Form(0),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    link = db.query(UserLink).filter(UserLink.id == lid, UserLink.user_id == current_user.id).first()
    if not link:
        raise HTTPException(status_code=404)
    link.title = title.strip() or link.title
    link.url = url.strip() or link.url
    link.description = description.strip()
    link.platform_id = platform_id if platform_id > 0 else None
    db.commit()
    return RedirectResponse(url="/dashboard?tab=links", status_code=302)


@router.get("/links/delete/{lid}")
def delete_link(lid: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    link = db.query(UserLink).filter(UserLink.id == lid, UserLink.user_id == current_user.id).first()
    if link:
        db.delete(link)
        db.commit()
    return RedirectResponse(url="/dashboard?tab=links", status_code=302)


@router.get("/go/{lid}")
def click_link(lid: int, request: Request, db: Session = Depends(get_db)):
    link = db.query(UserLink).filter(UserLink.id == lid).first()
    if not link:
        raise HTTPException(status_code=404)
    link.clicks_count = (link.clicks_count or 0) + 1
    db.commit()
    return RedirectResponse(url=link.url, status_code=302)
