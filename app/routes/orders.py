from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import (
    User, Customer, Item, Sale, SaleItem,
    PendingOrder, PendingOrderItem, OrderPayment, OrderStatusHistory
)
from app.auth import get_current_user, log_audit
from app.services import (
    next_code, money, apply_stock_change, add_customer_ledger,
    ensure_walk_in_customer, reserve_item_stock, release_item_stock,
    PAYMENT_METHODS, ORDER_STATUSES, FULFILLMENT_METHODS, get_shop_settings
)

router = APIRouter(prefix="/orders", tags=["pending-orders"])
templates = Jinja2Templates(directory="app/templates")


def parse_date_str(value: str, default: date = None) -> date:
    if not value:
        return default or date.today()
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except Exception:
        return default or date.today()


@router.get("", response_class=HTMLResponse)
def list_orders(
    request: Request,
    q: str = Query(""),
    status: str = Query(""),
    customer_id: str = Query(""),
    overdue_only: str = Query(""),
    fulfillment: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    ensure_walk_in_customer(db)

    # Base query for table
    query = db.query(PendingOrder).options(
        joinedload(PendingOrder.customer),
        joinedload(PendingOrder.creator),
        joinedload(PendingOrder.items)
    )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (PendingOrder.order_no.ilike(like)) |
            (PendingOrder.customer_name.ilike(like)) |
            (PendingOrder.customer_phone.ilike(like))
        )
    if status:
        query = query.filter(PendingOrder.status == status)
    if customer_id:
        try:
            query = query.filter(PendingOrder.customer_id == int(customer_id))
        except ValueError:
            pass
    if fulfillment:
        query = query.filter(PendingOrder.fulfillment_method == fulfillment)
    if date_from:
        query = query.filter(PendingOrder.order_date >= parse_date_str(date_from))
    if date_to:
        query = query.filter(PendingOrder.order_date <= parse_date_str(date_to))
    if overdue_only == "1":
        query = query.filter(
            PendingOrder.expected_date < today,
            PendingOrder.status.notin_(["Completed", "Cancelled", "Draft"])
        )

    orders = query.order_by(PendingOrder.order_date.desc(), PendingOrder.id.desc()).all()

    # Dashboard KPI metrics (calculated over full dataset)
    open_statuses = ["Pending", "Confirmed", "Preparing", "Ready for Collection", "Out for Delivery", "Partially Fulfilled"]
    
    total_pending = db.query(func.count(PendingOrder.id)).filter(
        PendingOrder.status.in_(open_statuses)
    ).scalar() or 0

    awaiting_prep = db.query(func.count(PendingOrder.id)).filter(
        PendingOrder.status.in_(["Pending", "Confirmed"])
    ).scalar() or 0

    ready_collection = db.query(func.count(PendingOrder.id)).filter(
        PendingOrder.status == "Ready for Collection"
    ).scalar() or 0

    out_delivery = db.query(func.count(PendingOrder.id)).filter(
        PendingOrder.status == "Out for Delivery"
    ).scalar() or 0

    overdue_count = db.query(func.count(PendingOrder.id)).filter(
        PendingOrder.expected_date < today,
        PendingOrder.status.in_(open_statuses)
    ).scalar() or 0

    total_outstanding = db.query(func.coalesce(func.sum(PendingOrder.balance_due), 0)).filter(
        PendingOrder.status.in_(open_statuses)
    ).scalar() or 0

    customers = db.query(Customer).order_by(Customer.name).all()

    return templates.TemplateResponse("orders/list.html", {
        "request": request,
        "current_user": current_user,
        "orders": orders,
        "customers": customers,
        "order_statuses": ORDER_STATUSES,
        "fulfillment_methods": FULFILLMENT_METHODS,
        "kpi": {
            "total_pending": total_pending,
            "awaiting_prep": awaiting_prep,
            "ready_collection": ready_collection,
            "out_delivery": out_delivery,
            "overdue_count": overdue_count,
            "total_outstanding": money(total_outstanding),
        },
        "filters": {
            "q": q,
            "status": status,
            "customer_id": customer_id,
            "overdue_only": overdue_only,
            "fulfillment": fulfillment,
            "date_from": date_from,
            "date_to": date_to,
        },
        "active_tab": "orders",
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })


@router.get("/new", response_class=HTMLResponse)
def new_order_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_walk_in_customer(db)
    customers = db.query(Customer).filter(Customer.status == "Active").order_by(Customer.name).all()
    items = db.query(Item).filter(Item.status == "Active").order_by(Item.brand, Item.name).all()
    next_ord_no = next_code(db, PendingOrder, "order_no", "ORD")

    return templates.TemplateResponse("orders/form.html", {
        "request": request,
        "current_user": current_user,
        "customers": customers,
        "items": items,
        "payment_methods": PAYMENT_METHODS,
        "fulfillment_methods": FULFILLMENT_METHODS,
        "order_statuses": ["Pending", "Confirmed", "Draft"],
        "next_order_no": next_ord_no,
        "today": date.today().isoformat(),
        "active_tab": "orders",
        "error": request.query_params.get("error"),
        "success": None,
    })


@router.post("/new")
async def create_order(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()

    customer_id = int(form.get("customer_id"))
    customer_name = (form.get("customer_name") or "").strip()
    customer_phone = (form.get("customer_phone") or "").strip()
    delivery_address = (form.get("delivery_address") or "").strip()
    fulfillment_method = form.get("fulfillment_method") or "Store Pickup"
    order_status = form.get("status") or "Pending"
    order_date = parse_date_str(form.get("order_date"))
    expected_date = parse_date_str(form.get("expected_date")) if form.get("expected_date") else None
    delivery_charges = money(form.get("delivery_charges") or 0)
    overall_discount = money(form.get("overall_discount") or form.get("discount") or 0)
    advance_payment = money(form.get("advance_payment") or form.get("advance_paid") or 0)
    payment_method = form.get("payment_method") or "Cash"
    notes = (form.get("notes") or form.get("note") or "").strip()
    order_status = form.get("status") or form.get("initial_status") or "Pending"

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")

    if not customer_name:
        customer_name = customer.name
    if not customer_phone and customer.phone:
        customer_phone = customer.phone

    item_ids = form.getlist("item_id") or form.getlist("item_id[]")
    variants = form.getlist("variant_info") or form.getlist("variant_info[]") or form.getlist("variant") or form.getlist("variant[]")
    quantities = form.getlist("quantity") or form.getlist("quantity[]")
    prices = form.getlist("unit_price") or form.getlist("unit_price[]")
    item_discounts = form.getlist("item_discount") or form.getlist("item_discount[]")

    lines = []
    subtotal = Decimal("0")

    for iid, var, qty, price, disc in zip(item_ids, variants, quantities, prices, item_discounts):
        if not iid or not qty:
            continue
        q = int(qty)
        p = money(price)
        d = money(disc or 0)
        if q <= 0:
            continue
        line_sub = money(q * (p - d))
        if line_sub < 0:
            line_sub = Decimal("0")
        lines.append({
            "item_id": int(iid),
            "variant_info": (var or "").strip(),
            "quantity": q,
            "unit_price": p,
            "discount": d,
            "subtotal": line_sub,
        })
        subtotal += line_sub

    if not lines:
        return RedirectResponse(url="/orders/new?error=Please+add+at+least+one+product+line", status_code=303)

    # Validate stock if status requires immediate reservation
    should_reserve = order_status in ["Confirmed", "Preparing", "Ready for Collection", "Out for Delivery"]
    if should_reserve:
        for line in lines:
            item = db.query(Item).filter(Item.id == line["item_id"]).first()
            if not item:
                return RedirectResponse(url=f"/orders/new?error=Item+not+found", status_code=303)
            if item.available_stock < line["quantity"]:
                return RedirectResponse(
                    url=f"/orders/new?error=Insufficient+available+stock+for+{item.item_code}+(Available:+{item.available_stock},+Requested:+{line['quantity']})",
                    status_code=303
                )
            if item.is_expired:
                return RedirectResponse(
                    url=f"/orders/new?error=Product+{item.item_code}+has+expired+and+cannot+be+ordered",
                    status_code=303
                )

    grand_total = max(Decimal("0"), subtotal - overall_discount + delivery_charges)
    if advance_payment > grand_total:
        advance_payment = grand_total
    balance_due = grand_total - advance_payment

    order_no = next_code(db, PendingOrder, "order_no", "ORD")

    order = PendingOrder(
        order_no=order_no,
        order_date=order_date,
        expected_date=expected_date,
        customer_id=customer.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        fulfillment_method=fulfillment_method,
        status=order_status,
        subtotal=subtotal,
        discount=overall_discount,
        delivery_charges=delivery_charges,
        total_amount=grand_total,
        advance_paid=advance_payment,
        balance_due=balance_due,
        notes=notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    for line in lines:
        item = db.query(Item).filter(Item.id == line["item_id"]).first()
        is_res = False
        if should_reserve:
            reserve_item_stock(db, item, line["quantity"])
            is_res = True

        order_item = PendingOrderItem(
            order_id=order.id,
            item_id=item.id,
            variant_info=line["variant_info"] or (f"{item.shade or ''} {item.size_volume or ''}").strip() or None,
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            discount=line["discount"],
            subtotal=line["subtotal"],
            is_reserved=is_res,
        )
        db.add(order_item)

    # Record advance payment if made
    if advance_payment > 0:
        pay_no = next_code(db, OrderPayment, "payment_no", "OPAY")
        payment = OrderPayment(
            order_id=order.id,
            payment_no=pay_no,
            date=order_date,
            amount=advance_payment,
            payment_method=payment_method,
            note=f"Initial deposit on order {order_no}",
            created_by=current_user.id,
        )
        db.add(payment)

    # Initial timeline entry
    timeline = OrderStatusHistory(
        order_id=order.id,
        from_status=None,
        to_status=order_status,
        note=f"Order created by {current_user.username}. Deposit: Rs. {advance_payment}",
        created_by=current_user.id,
    )
    db.add(timeline)

    db.commit()
    log_audit(db, current_user.id, "Create Pending Order", f"Created {order_no} for {customer_name} (Total: {grand_total}, Advance: {advance_payment})")
    return RedirectResponse(url=f"/orders/{order.id}?success=Order+{order_no}+created+successfully", status_code=303)


@router.get("/{order_id}", response_class=HTMLResponse)
def order_detail(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(PendingOrder).options(
        joinedload(PendingOrder.customer),
        joinedload(PendingOrder.creator),
        joinedload(PendingOrder.items).joinedload(PendingOrderItem.item),
        joinedload(PendingOrder.payments).joinedload(OrderPayment.user),
        joinedload(PendingOrder.timeline).joinedload(OrderStatusHistory.user),
        joinedload(PendingOrder.sale),
    ).filter(PendingOrder.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    settings = get_shop_settings(db)

    return templates.TemplateResponse("orders/detail.html", {
        "request": request,
        "current_user": current_user,
        "order": order,
        "settings": settings,
        "payment_methods": PAYMENT_METHODS,
        "order_statuses": ORDER_STATUSES,
        "active_tab": "orders",
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })


@router.post("/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    new_status = form.get("status") or form.get("new_status")
    note = (form.get("note") or form.get("status_notes") or "").strip()

    order = db.query(PendingOrder).options(
        joinedload(PendingOrder.items).joinedload(PendingOrderItem.item)
    ).filter(PendingOrder.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.status == "Completed":
        return RedirectResponse(url=f"/orders/{order_id}?error=Completed+orders+cannot+change+status", status_code=303)

    if order.status == "Cancelled":
        return RedirectResponse(url=f"/orders/{order_id}?error=Cancelled+orders+cannot+change+status", status_code=303)

    if new_status not in ORDER_STATUSES:
        return RedirectResponse(url=f"/orders/{order_id}?error=Invalid+status+selection", status_code=303)

    old_status = order.status
    if old_status == new_status:
        return RedirectResponse(url=f"/orders/{order_id}", status_code=303)

    # Handle transitions
    if new_status in ["Confirmed", "Preparing", "Ready for Collection", "Out for Delivery"]:
        # Reserve stock if not already reserved
        for line in order.items:
            if not line.is_reserved:
                try:
                    reserve_item_stock(db, line.item, line.quantity)
                    line.is_reserved = True
                except ValueError as ve:
                    db.rollback()
                    return RedirectResponse(url=f"/orders/{order_id}?error={str(ve).replace(' ', '+')}", status_code=303)

    elif new_status == "Cancelled":
        # Release any reservations
        for line in order.items:
            if line.is_reserved:
                release_item_stock(db, line.item, line.quantity)
                line.is_reserved = False

    elif new_status == "Draft":
        # If moving back to draft from confirmed, release reservations
        for line in order.items:
            if line.is_reserved:
                release_item_stock(db, line.item, line.quantity)
                line.is_reserved = False

    order.status = new_status
    timeline = OrderStatusHistory(
        order_id=order.id,
        from_status=old_status,
        to_status=new_status,
        note=note or f"Status changed from {old_status} to {new_status} by {current_user.username}",
        created_by=current_user.id,
    )
    db.add(timeline)
    db.commit()

    log_audit(db, current_user.id, "Update Order Status", f"Order {order.order_no} status changed from {old_status} to {new_status}")
    return RedirectResponse(url=f"/orders/{order_id}?success=Order+status+updated+to+{new_status}", status_code=303)


@router.post("/{order_id}/payment")
async def record_order_payment(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    amount = money(form.get("amount") or 0)
    payment_method = form.get("payment_method") or "Cash"
    pay_date = parse_date_str(form.get("date") or form.get("payment_date"))
    note = (form.get("note") or "").strip()

    order = db.query(PendingOrder).filter(PendingOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    if order.status in ["Completed", "Cancelled"]:
        return RedirectResponse(url=f"/orders/{order_id}?error=Cannot+add+payment+to+a+{order.status}+order", status_code=303)

    if amount <= 0:
        return RedirectResponse(url=f"/orders/{order_id}?error=Payment+amount+must+be+greater+than+0", status_code=303)

    if amount > order.balance_due:
        return RedirectResponse(
            url=f"/orders/{order_id}?error=Payment+amount+(Rs.+{amount})+exceeds+remaining+balance+(Rs.+{order.balance_due})",
            status_code=303
        )

    pay_no = next_code(db, OrderPayment, "payment_no", "OPAY")
    payment = OrderPayment(
        order_id=order.id,
        payment_no=pay_no,
        date=pay_date,
        amount=amount,
        payment_method=payment_method,
        note=note or f"Installment payment for order {order.order_no}",
        created_by=current_user.id,
    )
    db.add(payment)

    order.advance_paid = money(order.advance_paid + amount)
    order.balance_due = max(Decimal("0"), money(order.total_amount - order.advance_paid))

    timeline = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        note=f"Payment of Rs. {amount} received via {payment_method} by {current_user.username}. Balance remaining: Rs. {order.balance_due}",
        created_by=current_user.id,
    )
    db.add(timeline)

    db.commit()
    log_audit(db, current_user.id, "Record Order Payment", f"Recorded payment {pay_no} of Rs. {amount} for order {order.order_no}")
    return RedirectResponse(url=f"/orders/{order_id}?success=Payment+of+Rs.+{amount}+recorded+successfully", status_code=303)


@router.post("/{order_id}/complete")
async def complete_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    final_payment = money(form.get("final_payment") or 0)
    final_payment_method = form.get("final_payment_method") or "Cash"
    completion_note = (form.get("note") or "").strip()

    # Lock row or verify status
    order = db.query(PendingOrder).options(
        joinedload(PendingOrder.customer),
        joinedload(PendingOrder.items).joinedload(PendingOrderItem.item)
    ).filter(PendingOrder.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    # Idempotent safeguard: prevent completing twice
    if order.status == "Completed":
        return RedirectResponse(url=f"/orders/{order_id}?error=This+order+is+already+completed", status_code=303)

    if order.status == "Cancelled":
        return RedirectResponse(url=f"/orders/{order_id}?error=Cancelled+order+cannot+be+completed", status_code=303)

    # Validate stock quantities for all lines
    for line in order.items:
        # Check physical stock
        if line.item.current_stock < line.quantity:
            return RedirectResponse(
                url=f"/orders/{order_id}?error=Insufficient+physical+stock+for+{line.item.item_code}+(Physical:+{line.item.current_stock},+Required:+{line.quantity})",
                status_code=303
            )
        if line.item.is_expired:
            return RedirectResponse(
                url=f"/orders/{order_id}?error=Product+{line.item.item_code}+is+expired+and+cannot+be+dispensed",
                status_code=303
            )

    # Record any final settlement payment
    if final_payment > 0:
        if final_payment > order.balance_due:
            final_payment = order.balance_due
        pay_no = next_code(db, OrderPayment, "payment_no", "OPAY")
        payment = OrderPayment(
            order_id=order.id,
            payment_no=pay_no,
            date=date.today(),
            amount=final_payment,
            payment_method=final_payment_method,
            note="Final settlement payment at fulfillment",
            created_by=current_user.id,
        )
        db.add(payment)
        order.advance_paid = money(order.advance_paid + final_payment)
        order.balance_due = max(Decimal("0"), money(order.total_amount - order.advance_paid))

    total_received = money(order.advance_paid)
    remaining_balance = money(order.balance_due)

    # 1. Deduct physical stock & release reservations exactly once
    invoice_no = next_code(db, Sale, "invoice_no", "SINV")

    sale = Sale(
        invoice_no=invoice_no,
        date=date.today(),
        customer_id=order.customer_id,
        total_amount=order.total_amount,
        amount_received=total_received,
        balance=remaining_balance,
        payment_method=final_payment_method,
        note=f"Fulfilled Pending Order {order.order_no} | {completion_note}".strip(" |"),
        created_by=current_user.id,
    )
    db.add(sale)
    db.flush()

    for line in order.items:
        # Release reservation
        if line.is_reserved:
            release_item_stock(db, line.item, line.quantity)
            line.is_reserved = False

        # Deduct physical stock exactly once
        apply_stock_change(
            db=db,
            item=line.item,
            quantity_change=-line.quantity,
            movement_type="sale",
            user_id=current_user.id,
            reference_type="pending_order",
            reference_id=order.id,
            note=f"Order {order.order_no} ({invoice_no})"
        )

        # Add SaleItem
        db.add(SaleItem(
            sale_id=sale.id,
            item_id=line.item_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal=line.subtotal
        ))

    # 2. Update customer ledger if registered customer
    customer = order.customer
    if customer and not customer.is_walk_in:
        add_customer_ledger(
            db=db,
            customer=customer,
            entry_date=date.today(),
            description=f"Order {order.order_no} completed ({invoice_no})",
            debit=order.total_amount,
            reference_type="order_fulfillment",
            reference_id=order.id
        )
        if total_received > 0:
            add_customer_ledger(
                db=db,
                customer=customer,
                entry_date=date.today(),
                description=f"Payment on {order.order_no} ({invoice_no})",
                credit=total_received,
                reference_type="order_payment",
                reference_id=order.id
            )

    # 3. Update order state
    old_status = order.status
    order.status = "Completed"
    order.sale_id = sale.id
    order.completed_at = datetime.now()

    timeline = OrderStatusHistory(
        order_id=order.id,
        from_status=old_status,
        to_status="Completed",
        note=f"Order completed & fulfilled into Sales Invoice {invoice_no}. Total received: Rs. {total_received}, Balance: Rs. {remaining_balance}. By {current_user.username}",
        created_by=current_user.id,
    )
    db.add(timeline)

    db.commit()
    log_audit(db, current_user.id, "Complete Order", f"Order {order.order_no} completed -> Generated Invoice {invoice_no} (Total: {order.total_amount})")
    return RedirectResponse(url=f"/orders/{order.id}?success=Order+{order.order_no}+successfully+completed!+Sales+Invoice+{invoice_no}+generated.", status_code=303)
