from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import stripe
from pydantic import BaseModel

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user

router = APIRouter()


class BuyerConfirmRequest(BaseModel):
    token: str


@router.post("/{order_id}/buyer-confirm")
def buyer_confirm_delivery(
    order_id: int,
    body: BuyerConfirmRequest,
    db: Session = Depends(get_db)
):
    token = body.token
    buyer = get_current_user(db, token)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status != "delivered":
        raise HTTPException(status_code=400, detail="Order not delivered yet")

    traveler = db.query(User).filter(User.id == order.traveler_id).first()
    if not traveler or not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    amount = int(order.traveler_fee * 100)

    try:
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="usd",
            destination=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe transfer failed: {str(e)}")

    order.status = "paid"
    order.stripe_transfer_id = transfer.id
    order.buyer_confirmed_at = datetime.utcnow()

    trip = db.query(Trip).filter(Trip.id == order.trip_id).first()
    if trip:
        trip.total_earned += order.traveler_fee

    event = OrderEvent(
        order_id=order.id,
        event_type="buyer_confirmed",
        description=f"Buyer confirmed delivery. Transfer {transfer.id} sent to traveler.",
        created_at=datetime.utcnow()
    )
    db.add(event)

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "order_id": order.id,
        "transfer_id": transfer.id,
        "amount": amount
    }

















    
