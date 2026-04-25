from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils.db import get_db
from db_utils.models import Order, Trip, User
from utils.auth import get_current_user
from utils.fees import calculate_fees

router = APIRouter()


# ---------------------------------------------------------
# BUYER CREATES ORDER
# ---------------------------------------------------------
@router.post("/create")
def create_order(
    item_name: str,
    item_price: float,
    store_name: str,
    pickup_location: str,
    delivery_location: str,
    token: str,
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, token)

    if buyer.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can create orders")

    fees = calculate_fees(item_price)

    new_order = Order(
        buyer_id=buyer.id,
        item_name=item_name,
        item_price=item_price,
        store_name=store_name,
        pickup_location=pickup_location,
        delivery_location=delivery_location,
        platform_fee=fees["platform_fee"],
        traveler_fee=fees["traveler_fee"],
        total_charged=fees["total_charged"],
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return {
        "status": "success",
        "order_id": new_order.id,
        "total_charged": new_order.total_charged,
    }


# ---------------------------------------------------------
# TRAVELER ACCEPTS ORDER
# ---------------------------------------------------------
@router.post("/{order_id}/accept")
def accept_order(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can accept orders")

    order = db












    
