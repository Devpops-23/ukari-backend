from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import stripe
from pydantic import BaseModel

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user
from utils.fees import calculate_fees

router = APIRouter()


class CreateOrderRequest(BaseModel):
    item_name: str
    item_price: float
    store_name: str
    pickup_location: str
    delivery_location: str
    token: str


@router.post("/create")
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

    return {
        "status": "success",
        "order_id": new_order.id,
        "total_charged": new_order.total_charged,
    }


















    
