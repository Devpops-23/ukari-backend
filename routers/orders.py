from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import stripe
from pydantic import BaseModel

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user

router = APIRouter(
    prefix="/walmart",
    tags=["Walmart Purchasing"]
)

# -------------------------------
# Walmart Purchase Request Model
# -------------------------------
class WalmartPurchaseRequest(BaseModel):
    item_name: str
    item_price_cents: int
    platform_fee_cents: int
    traveler_fee_cents: int
    weight_lbs: float
    size_description: str
    restricted_item: bool
    buyer_id: int
    traveler_id: int
    trip_id: int | None = None


# -------------------------------
# Buyer Confirm Request Model
# -------------------------------
class BuyerConfirmRequest(BaseModel):
    token: str


# -------------------------------
# Create Walmart Order
# -------------------------------
@router.post("/create-order")
def create_walmart_order(
    payload: WalmartPurchaseRequest,
    db: Session = Depends(get_db)
):
 order = Order(
    item_name=payload.item_name,
    item_price_cents=payload.item_price_cents,
    platform_fee_cents=payload.platform_fee_cents,
    traveler_fee_cents=payload.traveler_fee_cents,
    total_charged_cents=(
        payload.item_price_cents +
        payload.platform_fee_cents +
        payload.traveler_fee_cents
    ),
    weight_lbs=payload.weight_lbs,
    size_description=payload.size_description,
    restricted_item=payload.restricted_item,
    buyer_id=payload.buyer_id,
    traveler_id=payload.traveler_id,
    trip_id=payload.trip_id,
    merchant_name="amazon",
    status="pending",
    created_at=datetime.utcnow()
)
  

@router.post("/create-order")
def create_order(order_data: WalmartOrderCreate, db: Session = Depends(get_db)):
    order = Order(
        buyer_id=order_data.buyer_id,
        merchant_name=order_data.merchant_name,
        item_name=order_data.item_name,
        item_price_cents=order_data.item_price_cents,
        traveler_fee_cents=order_data.traveler_fee_cents,
        platform_fee_cents=order_data.platform_fee_cents,
        status="created"
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {"order_id": order.id, "status": order.status}



# -------------------------------
# Traveler Accept Order
# -------------------------------
@router.post("/{order_id}/accept")
def accept_order(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can accept orders")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order already accepted or completed")

    order.traveler_id = traveler.id
    order.status = "accepted"

    event = OrderEvent(
        order_id=order.id,
        event_type="accepted",
        description=f"Traveler {traveler.id} accepted the Walmart order.",
        created_at=datetime.utcnow()
    )
    db.add(event)

    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id}


# -------------------------------
# Traveler Marks Delivered
# -------------------------------
@router.post("/{order_id}/deliver")
def mark_delivered(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    traveler = get_current_user(db, token)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.traveler_id != traveler.id:
        raise HTTPException(status_code=403, detail="Not your order")

    order.status = "delivered"
    order.delivered_at = datetime.utcnow()

    event = OrderEvent(
        order_id=order.id,
        event_type="delivered",
        description="Traveler marked the Walmart order as delivered.",
        created_at=datetime.utcnow()
    )
    db.add(event)

    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id}


# -------------------------------
# Buyer Confirms Delivery → Stripe Transfer
# -------------------------------
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

    amount = order.traveler_fee_cents

    transfer = stripe.Transfer.create(
        amount=amount,
        currency="usd",
        destination=traveler.stripe_account_id
    )

    order.status = "paid"
    order.stripe_transfer_id = transfer.id
    order.buyer_confirmed_at = datetime.utcnow()

    trip = db.query(Trip).filter(Trip.id == order.trip_id).first()
    if trip:
        trip.total_earned += (order.traveler_fee_cents / 100)

    event = OrderEvent(
        order_id=order.id,
        event_type="buyer_confirmed",
        description=f"Buyer confirmed Walmart delivery. Transfer {transfer.id} sent to traveler.",
        created_at=datetime.utcnow()
    )
    db.add(event)

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "order_id": order.id,
        "transfer_id": transfer.id,
        "amount_cents": amount
    }


# -------------------------------
# Get Order Status
# -------------------------------
@router.get("/{order_id}/status")
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"order_id": order.id, "status": order.status}



















    
