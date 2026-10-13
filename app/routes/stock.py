from decimal import Decimal
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query, UploadFile, File
import os, shutil, uuid
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Item, StockMovement, ItemCategory, ItemDescription
from app.auth import get_current_user, log_audit
from app.services import next_code, apply_stock_change, money

router = APIRouter(prefix="/stock", tags=["stock"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_items(
    request: Request,
    q: str = Query(""),
    brand: str = Query(""),
    category: str = Query(""),
    low_stock: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Item.item_code.ilike(like)) |
            (Item.brand.ilike(like)) |
            (Item.barcode.ilike(like)) |
            (Item.name.ilike(like))
        )
    if brand:
        query = query.filter(Item.brand.ilike(f"%{brand}%"))
    if category:
        query = query.filter(Item.category == category)
    if low_stock:
        query = query.filter(Item.current_stock <= Item.reorder_level)

    items = query.order_by(Item.item_code).all()
    brands = [r[0] for r in db.query(Item.brand).distinct().order_by(Item.brand).all() if r[0]]
    categories = [c.name for c in db.query(ItemCategory).order_by(ItemCategory.name).all()]
    return templates.TemplateResponse("stock/list.html", {
        "request": request,
        "current_user": current_user,
        "items": items,
        "categories": categories,
        "brands": brands,
        "filters": {"q": q, "brand": brand, "category": category, "low_stock": low_stock},
        "active_tab": "stock",
        "error": None,
        "success": None,
    })


@router.get("/low", response_class=HTMLResponse)
@router.get("/low", response_class=HTMLResponse)
def low_stock_report(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.current_stock <= Item.reorder_level, Item.status == "Active").order_by(Item.current_stock).all()
    return templates.TemplateResponse("stock/low.html", {
        "request": request, "current_user": current_user, "items": items, "active_tab": "stock",
        "error": None, "success": None,
    })


@router.get("/expiring", response_class=HTMLResponse)
def expiring_report(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import date, timedelta
    today = date.today()
    limit_date = today + timedelta(days=60)
    items = db.query(Item).filter(
        Item.expiry_date != None,
        Item.expiry_date <= limit_date,
        Item.status == "Active"
    ).order_by(Item.expiry_date).all()
    return templates.TemplateResponse("stock/expiring.html", {
        "request": request, "current_user": current_user, "items": items, "active_tab": "stock",
        "today": today, "error": None, "success": None,
    })


@router.get("/new", response_class=HTMLResponse)
def new_item_form(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    categories = [c.name for c in db.query(ItemCategory).order_by(ItemCategory.name).all()]
    types = [t.name for t in db.query(ItemDescription).order_by(ItemDescription.name).all()]
    return templates.TemplateResponse("stock/form.html", {
        "request": request, "current_user": current_user, "item": None,
        "categories": categories, "types": types, "active_tab": "stock",
        "error": None, "success": None,
    })


@router.post("/new")
def create_item(
    request: Request,
    brand: str = Form(...),
    barcode: str = Form(""),
    name: str = Form(""),
    description: str = Form(""),
    category: str = Form(...),
    shade: str = Form(""),
    size_volume: str = Form(""),
    skin_type: str = Form(""),
    purchase_price: str = Form("0"),
    sale_price: str = Form("0"),
    discount: str = Form("0"),
    reorder_level: int = Form(5),
    batch_no: str = Form(""),
    expiry_date: str = Form(""),
    unit: str = Form("Piece"),
    status: str = Form("Active"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    code = next_code(db, Item, "item_code", "ITM")
    exp_dt = None
    if expiry_date.strip():
        try:
            exp_dt = datetime.strptime(expiry_date.strip(), "%Y-%m-%d").date()
        except Exception:
            exp_dt = None

    item = Item(
        item_code=code,
        brand=brand.strip(),
        name=name.strip(),
        barcode=barcode.strip() or None,
        description=description.strip() or None,
        category=category,
        shade=shade.strip() or None,
        size_volume=size_volume.strip() or None,
        skin_type=skin_type.strip() or None,
        purchase_price=money(purchase_price),
        sale_price=money(sale_price),
        discount=money(discount),
        current_stock=0,
        reserved_stock=0,
        reorder_level=reorder_level,
        batch_no=batch_no.strip() or None,
        expiry_date=exp_dt,
        unit=unit,
        status=status,
    )
    db.add(item)
    db.commit()
    log_audit(db, current_user.id, "Create Item", f"Created item {code} — {brand} {name.strip()}")
    return RedirectResponse(url="/stock", status_code=303)


@router.get("/{item_id}", response_class=HTMLResponse)
def item_detail(item_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    movements = db.query(StockMovement).filter(StockMovement.item_id == item_id).order_by(StockMovement.created_at.desc()).all()
    return templates.TemplateResponse("stock/detail.html", {
        "request": request, "current_user": current_user, "item": item, "movements": movements,
        "active_tab": "stock", "error": None, "success": None,
    })


@router.get("/{item_id}/edit", response_class=HTMLResponse)
def edit_item_form(item_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    categories = [c.name for c in db.query(ItemCategory).order_by(ItemCategory.name).all()]
    types = [t.name for t in db.query(ItemDescription).order_by(ItemDescription.name).all()]
    return templates.TemplateResponse("stock/form.html", {
        "request": request, "current_user": current_user, "item": item,
        "categories": categories, "types": types, "active_tab": "stock",
        "error": None, "success": None,
    })


@router.post("/{item_id}/edit")
def update_item(
    item_id: int,
    request: Request,
    brand: str = Form(...),
    barcode: str = Form(""),
    name: str = Form(""),
    description: str = Form(""),
    category: str = Form(...),
    shade: str = Form(""),
    size_volume: str = Form(""),
    skin_type: str = Form(""),
    purchase_price: str = Form("0"),
    sale_price: str = Form("0"),
    discount: str = Form("0"),
    reorder_level: int = Form(5),
    batch_no: str = Form(""),
    expiry_date: str = Form(""),
    unit: str = Form("Piece"),
    status: str = Form("Active"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    exp_dt = None
    if expiry_date.strip():
        try:
            exp_dt = datetime.strptime(expiry_date.strip(), "%Y-%m-%d").date()
        except Exception:
            exp_dt = None

    item.brand = brand.strip()
    item.name = name.strip()
    item.barcode = barcode.strip() or None
    item.description = description.strip() or None
    item.category = category
    item.shade = shade.strip() or None
    item.size_volume = size_volume.strip() or None
    item.skin_type = skin_type.strip() or None
    item.purchase_price = money(purchase_price)
    item.sale_price = money(sale_price)
    item.discount = money(discount)
    item.reorder_level = reorder_level
    item.batch_no = batch_no.strip() or None
    item.expiry_date = exp_dt
    item.unit = unit
    item.status = status

    db.commit()
    log_audit(db, current_user.id, "Update Item", f"Updated item {item.item_code}")
    return RedirectResponse(url=f"/stock/{item_id}", status_code=303)


@router.get("/{item_id}/adjust", response_class=HTMLResponse)
def adjust_form(item_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    return templates.TemplateResponse("stock/adjust.html", {
        "request": request, "current_user": current_user, "item": item,
        "active_tab": "stock", "error": None, "success": None,
    })


@router.post("/{item_id}/adjust")
def adjust_stock(
    item_id: int,
    request: Request,
    quantity_change: int = Form(...),
    reason: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if not reason.strip():
        return templates.TemplateResponse("stock/adjust.html", {
            "request": request, "current_user": current_user, "item": item,
            "active_tab": "stock", "error": "Reason is required", "success": None,
        })
    try:
        apply_stock_change(
            db, item, quantity_change, "adjustment",
            user_id=current_user.id, reference_type="adjustment", note=reason.strip()
        )
        db.commit()
        log_audit(db, current_user.id, "Stock Adjustment", f"{item.item_code}: {quantity_change:+d} — {reason}")
    except ValueError as e:
        return templates.TemplateResponse("stock/adjust.html", {
            "request": request, "current_user": current_user, "item": item,
            "active_tab": "stock", "error": str(e), "success": None,
        })
    return RedirectResponse(url=f"/stock/{item_id}", status_code=303)


@router.post("/{item_id}/delete")
def delete_item(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    
    item_code = item.item_code
    has_history = db.query(StockMovement).filter(StockMovement.item_id == item_id).first() is not None
    if has_history:
        item.status = "Discontinued"
        db.commit()
        log_audit(db, current_user.id, "Deactivate Item", f"Discontinued item {item_code} (has transaction history)")
        return RedirectResponse(url="/stock", status_code=303)

    db.delete(item)
    db.commit()
    log_audit(db, current_user.id, "Delete Item", f"Deleted item {item_code}")
    return RedirectResponse(url="/stock", status_code=303)
