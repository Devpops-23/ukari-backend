from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import os

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user

router = APIRouter()

# ---------------------------------------------------------
# U-KARI FEE ENGINE (FLAT FEES)
# ---------------------------------------------------------

PLATFORM_FEE = 10.0
TRAVELER_FEE = 25.0

def calculate_fees(item_price: float):
    platform_fee = PLATFORM_FEE
    traveler_fee = TRAVELER_FEE
    total_charged = item_price + platform_fee + traveler_fee

    return {
        "platform_fee": platform_fee,
        "traveler_fee": traveler_fee,
        "total_charged": total_charged
    }


# ---------------------------------------------------------
# BUYER CREATES ORDER
# ---------------------------------------------------------
@router.post("/orders/create")
def create_order(
    item_price: float,
    store_name: str,
    pickup_location: str,
    delivery_location: str,
    db: Session = Depends(get_db),
    buyer: User = Depends(get_current_user)
):
    if buyer.status == "banned":
        raise HTTPException(
            status_code=403,
            detail="Your account is restricted and cannot place orders."
        )

    if buyer.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can create orders")

    fees = calculate_fees(item_price)

    order = Order(
        buyer_id=buyer.id,
        item_price=item_price,
        platform_fee=fees["platform_fee"],
        traveler_fee=fees["traveler_fee"],
        total_charged=fees["total_charged"],
        store_name=store_name,
        pickup_location=pickup_location,
        delivery_location=delivery_location,
        shipment_status="pending",
        status="pending"
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    event = OrderEvent(
        order_id=order.id,
        event_type="order_created",
        message="Order created and awaiting traveler assignment."
    )
    db.add(event)
    db.commit()

    return {
        "status": "success",
        "order_id": order.id,
        "item_price": item_price,
        "platform_fee": fees["platform_fee"],
        "traveler_fee": fees["traveler_fee"],
        "total_charged": fees["total_charged"]
    }


# ---------------------------------------------------------
# BUYER CONFIRMS DELIVERY
# ---------------------------------------------------------
@router.post("/orders/{order_id}/buyer-confirm")
def buyer_confirm_delivery(
    order_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    order.status = "buyer_confirmed"
    order.buyer_confirmed_at = datetime.utcnow()
    order.amount_earned = order.traveler_fee

    db.commit()

    traveler = db.query(User).filter(User.id == order.traveler_id).first()

    if traveler:
        if order.delivered_at and order.delivery_deadline:
            if order.delivered_at <= order.delivery_deadline:
                traveler.on_time_deliveries += 1
            else:
                traveler.late_deliveries += 1
        db.commit()

    event = OrderEvent(
        order_id=order.id,
        event_type="delivery_confirmed",
        message="Buyer confirmed delivery. Traveler payout will be released."
    )
    db.add(event)
    db.commit()

    return {"status": "success", "message": "Delivery confirmed."}



