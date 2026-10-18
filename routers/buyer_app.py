from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user, get_current_buyer
from utils.fees import calculate_fees

router = APIRouter(tags=["Buyer"])

oauth2_scheme = HTTPBearer(auto_error=False)


# -------------------------------
# Request Models
# -------------------------------
class CreateOrderRequest(BaseModel):
    item_name: str
    item_price: float
    store_name: Optional[str] = "walmart"
    pickup_location: Optional[str] = ""
    delivery_location: Optional[str] = ""


class DisputeOrderRequest(BaseModel):
    reason: Optional[str] = "Item not received / defective"
    description: Optional[str] = ""


class ConfirmDeliveryRequest(BaseModel):
    token: Optional[str] = None


class RateTravelerRequest(BaseModel):
    token: Optional[str] = None
    rating: int = 5


def format_buyer_order(order: Order):
    price = order.item_price or (order.item_price_cents / 100.0 if order.item_price_cents else 0.0)
    traveler_fee = order.traveler_fee or (order.traveler_fee_cents / 100.0 if order.traveler_fee_cents else 0.0)
    platform_fee = order.platform_fee or (order.platform_fee_cents / 100.0 if order.platform_fee_cents else 0.0)
    total_charged = order.total_charged or (order.total_charged_cents / 100.0 if order.total_charged_cents else price + traveler_fee + platform_fee)

    return {
        "id": order.id,
        "order_id": order.id,
        "item_name": order.item_name,
        "store_name": order.store_name or order.merchant_name or "walmart",
        "price": price,
        "item_price": price,
        "traveler_fee": traveler_fee,
        "platform_fee": platform_fee,
        "total_charged": total_charged,
        "pickup_location": order.pickup_location,
        "delivery_location": order.delivery_location,
        "status": order.status,
        "buyer_id": order.buyer_id,
        "traveler_id": order.traveler_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "dispute_reason": order.dispute_reason,
        "dispute_status": order.dispute_status,
    }


# -------------------------------
# Buyer Creates an Order
# -------------------------------
@router.post("/buyer/orders/create")
@router.post("/orders/create")
def create_order(
    body: CreateOrderRequest,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fees = calculate_fees(body.item_price)

    item_price_cents = int(body.item_price * 100)
    platform_fee_cents = int(fees["platform_fee"] * 100)
    traveler_fee_cents = int(fees["traveler_fee"] * 100)
    total_charged_cents = int(fees["total_charged"] * 100)

    new_order = Order(
        buyer_id=buyer.id,
        item_name=body.item_name,
        item_price=body.item_price,
        item_price_cents=item_price_cents,
        store_name=body.store_name or "walmart",
        merchant_name=body.store_name or "walmart",
        pickup_location=body.pickup_location or "",
        delivery_location=body.delivery_location or "",
        platform_fee=fees["platform_fee"],
        platform_fee_cents=platform_fee_cents,
        traveler_fee=fees["traveler_fee"],
        traveler_fee_cents=traveler_fee_cents,
        total_charged=fees["total_charged"],
        total_charged_cents=total_charged_cents,
        amount_earned=fees["traveler_fee"],
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Create event
    event = OrderEvent(
        order_id=new_order.id,
        event_type="order_created",
        description="Buyer created the order.",
        message="Buyer created the order.",
        created_at=datetime.utcnow(),
    )

    db.add(event)
    db.commit()

    return {
        "status": "success",
        "order_id": new_order.id,
        "total_charged": new_order.total_charged,
        "order": format_buyer_order(new_order),
    }


# -------------------------------
# Buyer Gets All Orders
# -------------------------------
@router.get("/buyer/orders")
@router.get("/orders/buyer")
def get_buyer_orders(
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.buyer_id == buyer.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    formatted = [format_buyer_order(o) for o in orders]
    return {"status": "success", "orders": formatted}


# -------------------------------
# Buyer Gets a Single Order
# -------------------------------
@router.get("/buyer/orders/{order_id}")
@router.get("/orders/buyer/{order_id}")
def get_buyer_order(
    order_id: int,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id and buyer.role != "admin":
        raise HTTPException(status_code=403, detail="Not your order")

    return format_buyer_order(order)


# -------------------------------
# Buyer Disputes an Order
# -------------------------------
@router.post("/orders/buyer/{order_id}/dispute")
@router.post("/buyer/orders/{order_id}/dispute")
def dispute_order(
    order_id: int,
    body: DisputeOrderRequest,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id and buyer.role != "admin":
        raise HTTPException(status_code=403, detail="Not your order")

    order.status = "disputed"
    order.dispute_status = "pending"
    order.dispute_reason = body.reason
    order.disputed_at = datetime.utcnow()
    order.dispute_created_at = datetime.utcnow()

    event = OrderEvent(
        order_id=order.id,
        event_type="dispute_opened",
        description=f"Buyer filed dispute: {body.reason}",
        message=body.description or body.reason,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Dispute submitted", "order_id": order.id}


# -------------------------------
# Buyer Cancels an Order
# -------------------------------
@router.post("/buyer/orders/{order_id}/cancel")
@router.post("/orders/buyer/{order_id}/cancel")
def cancel_order(
    order_id: int,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id and buyer.role != "admin":
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status not in ["pending", "created"]:
        raise HTTPException(status_code=400, detail="Only pending orders can be canceled")

    order.status = "canceled"

    event = OrderEvent(
        order_id=order.id,
        event_type="canceled",
        description="Buyer canceled the order.",
        message="Buyer canceled the order.",
        created_at=datetime.utcnow(),
    )

    db.add(event)
    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id, "message": "Order canceled"}


# -------------------------------
# Buyer Confirms Delivery
# -------------------------------
@router.post("/buyer/orders/{order_id}/confirm")
@router.post("/orders/buyer/{order_id}/confirm")
def confirm_delivery(
    order_id: int,
    body: Optional[ConfirmDeliveryRequest] = None,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "buyer_confirmed"
    order.buyer_confirmed_at = datetime.utcnow()

    event = OrderEvent(
        order_id=order.id,
        event_type="delivery_confirmed",
        description="Buyer confirmed package delivery.",
        message="Buyer confirmed package delivery.",
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id, "order": format_buyer_order(order)}


# -------------------------------
# Buyer Rates Traveler
# -------------------------------
@router.post("/buyer/orders/{order_id}/rate")
@router.post("/orders/buyer/{order_id}/rate")
def rate_traveler(
    order_id: int,
    body: RateTravelerRequest,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.traveler_id:
        traveler = db.query(User).filter(User.id == order.traveler_id).first()
        if traveler:
            traveler.rating = round((traveler.rating + body.rating) / 2.0 if traveler.rating > 0 else float(body.rating), 2)
            traveler.on_time_deliveries = (traveler.on_time_deliveries or 0) + 1
            db.commit()

    event = OrderEvent(
        order_id=order.id,
        event_type="traveler_rated",
        description=f"Buyer rated traveler with {body.rating} stars.",
        message=f"Rating: {body.rating}",
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()

    return {"status": "success", "rating": body.rating}


# -------------------------------
# Buyer Tracks Order
# -------------------------------
@router.get("/buyer/orders/{order_id}/track")
@router.get("/orders/buyer/{order_id}/track")
def track_order(
    order_id: int,
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"status": "success", "order": format_buyer_order(order)}






