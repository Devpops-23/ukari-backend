from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user
from utils.fees import calculate_fees

router = APIRouter()


# -------------------------------
# Create Order Request Model
# -------------------------------
class CreateOrderRequest(BaseModel):
    item_name: str
    item_price: float
    store_name: str
    pickup_location: str
    delivery_location: str
    token: str


# -------------------------------
# Buyer Creates an Order
# -------------------------------
@router.post("/orders/create")
def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, body.token)

    if buyer.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can create orders")

    fees = calculate_fees(body.item_price)

    new_order = Order(
        buyer_id=buyer.id,
        item_name=body.item_name,
        item_price=body.item_price,
        store_name=body.store_name,
        pickup_location=body.pickup_location,
        delivery_location=body.delivery_location,
        platform_fee=fees["platform_fee"],
        traveler_fee=fees["traveler_fee"],
        total_charged=fees["total_charged"],
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    event = OrderEvent(
        order_id=new_order.id,
        event_type="created",
        description="Buyer created the order.",
        created_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()

    return {
        "status": "success",
        "order_id": new_order.id,
        "total_charged": new_order.total_charged,
    }


# -------------------------------
# Buyer Gets All Their Orders
# -------------------------------
@router.get("/orders")
def get_buyer_orders(
    token: str,
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, token)

    orders = (
        db.query(Order)
        .filter(Order.buyer_id == buyer.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return {"orders": orders}


# -------------------------------
# Buyer Gets a Single Order
# -------------------------------
@router.get("/orders/{order_id}")
def get_buyer_order(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, token)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Not your order")

    return order


# -------------------------------
# Buyer Cancels an Order (Optional)
# -------------------------------
@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, token)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be canceled")

    order.status = "canceled"

    event = OrderEvent(
        order_id=order.id,
        event_type="canceled",
        description="Buyer canceled the order.",
        created_at=datetime.utcnow()
    )
    db.add(event)

    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id, "message": "Order canceled"}




