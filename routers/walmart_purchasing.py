
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user


MAX_ITEM_WEIGHT_LBS = 10.0

router = APIRouter(
    prefix="/walmart",
    tags=["Walmart Purchasing"],
)


def utc_now():
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# --------------------------------------------------
# Walmart Purchase Request Model
# --------------------------------------------------
class WalmartPurchaseRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    item_price_cents: int = Field(ge=0)
    platform_fee_cents: int = Field(ge=0)
    product_url: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1)
    weight_lbs: float = Field(gt=0, le=MAX_ITEM_WEIGHT_LBS)
    traveler_fee_cents: int = Field(ge=0)
    size_description: str = Field(min_length=1)
    restricted_item: bool
    buyer_id: int = Field(gt=0)
    traveler_id: int = Field(gt=0)
    trip_id: int | None = None


# --------------------------------------------------
# Buyer Confirmation Request
# --------------------------------------------------
class BuyerConfirmRequest(BaseModel):
    token: str = Field(min_length=1)


# --------------------------------------------------
# Create Walmart Order
# --------------------------------------------------
@router.post("/create-order")
def create_walmart_order(
    payload: WalmartPurchaseRequest,
    db: Session = Depends(get_db),
):
    # Never allow restricted items to be ordered.
    if payload.restricted_item:
        raise HTTPException(
            status_code=400,
            detail="Restricted items cannot be purchased through U-KARI.",
        )

    # Validate buyer exists.
    buyer = db.query(User).filter(
        User.id == payload.buyer_id
    ).first()

    if not buyer:
        raise HTTPException(
            status_code=404,
            detail="Buyer not found.",
        )

    # Validate traveler exists.
    traveler = db.query(User).filter(
        User.id == payload.traveler_id
    ).first()

    if not traveler:
        raise HTTPException(
            status_code=404,
            detail="Traveler not found.",
        )

    if traveler.role != "traveler":
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a traveler.",
        )

    # Validate optional trip.
    if payload.trip_id is not None:
        trip = db.query(Trip).filter(
            Trip.id == payload.trip_id
        ).first()

        if not trip:
            raise HTTPException(
                status_code=404,
                detail="Trip not found.",
            )

    order = Order(
        item_name=payload.item_name,
        item_price_cents=payload.item_price_cents,
        platform_fee_cents=payload.platform_fee_cents,
        traveler_fee_cents=payload.traveler_fee_cents,
        weight_lbs=payload.weight_lbs,
        size_description=payload.size_description,
        restricted_item=False,
        buyer_id=payload.buyer_id,
        traveler_id=payload.traveler_id,
        trip_id=payload.trip_id,
        merchant_name="walmart",
        status="pending",
        created_at=utc_now(),
    )

    try:
        db.add(order)
        db.flush()

        event = OrderEvent(
            order_id=order.id,
            event_type="created",
            description=(
                f"Walmart order created for buyer {payload.buyer_id} "
                f"and traveler {payload.traveler_id}."
            ),
            created_at=utc_now(),
        )

        db.add(event)
        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise

    return {
        "status": "success",
        "order_id": order.id,
        "merchant": "walmart",
        "order_status": order.status,
        "quantity": payload.quantity,
        "weight_per_item_lbs": payload.weight_lbs,
        "total_weight_lbs": round(
            payload.weight_lbs * payload.quantity, 2
        ),
    }


# --------------------------------------------------
# Traveler Accepts Order
# --------------------------------------------------
@router.post("/{order_id}/accept")
def accept_order(
    order_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(
            status_code=403,
            detail="Only travelers can accept orders.",
        )

    order = db.query(Order).filter(
        Order.id == order_id
    ).with_for_update().first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Order is no longer available for acceptance.",
        )

    # An order is offered to the designated traveler.
    if order.traveler_id != traveler.id:
        raise HTTPException(
            status_code=403,
            detail="This order is assigned to another traveler.",
        )

    try:
        order.status = "accepted"

        db.add(
            OrderEvent(
                order_id=order.id,
                event_type="accepted",
                description=(
                    f"Traveler {traveler.id} accepted the Walmart order."
                ),
                created_at=utc_now(),
            )
        )

        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise

    return {
        "status": "success",
        "order_id": order.id,
        "order_status": order.status,
    }


# --------------------------------------------------
# Traveler Marks Order Delivered
# --------------------------------------------------
@router.post("/{order_id}/deliver")
def mark_delivered(
    order_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(
            status_code=403,
            detail="Only travelers can mark orders as delivered.",
        )

    order = db.query(Order).filter(
        Order.id == order_id
    ).with_for_update().first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.traveler_id != traveler.id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this order.",
        )

    if order.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail="Only accepted orders can be marked delivered.",
        )

    try:
        order.status = "delivered"
        order.delivered_at = utc_now()

        db.add(
            OrderEvent(
                order_id=order.id,
                event_type="delivered",
                description=(
                    "Traveler marked the Walmart order as delivered."
                ),
                created_at=utc_now(),
            )
        )

        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise

    return {
        "status": "success",
        "order_id": order.id,
        "order_status": order.status,
    }


# --------------------------------------------------
# Buyer Confirms Delivery -> Stripe Transfer
# --------------------------------------------------
@router.post("/{order_id}/buyer-confirm")
def buyer_confirm_delivery(
    order_id: int,
    body: BuyerConfirmRequest,
    db: Session = Depends(get_db),
):
    buyer = get_current_user(db, body.token)

    order = db.query(Order).filter(
        Order.id == order_id
    ).with_for_update().first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.buyer_id != buyer.id:
        raise HTTPException(
            status_code=403,
            detail="You are not the buyer for this order.",
        )

    if order.status != "delivered":
        raise HTTPException(
            status_code=400,
            detail="The order must be delivered before confirmation.",
        )

    traveler = db.query(User).filter(
        User.id == order.traveler_id
    ).first()

    if not traveler or not traveler.stripe_account_id:
        raise HTTPException(
            status_code=400,
            detail="Traveler has no connected Stripe account.",
        )

    amount = order.traveler_fee_cents

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Traveler payout must be greater than zero.",
        )

    try:
        # Stripe must be configured with your secret API key elsewhere.
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="usd",
            destination=traveler.stripe_account_id,
            description=f"U-KARI Walmart order #{order.id}",
            idempotency_key=f"walmart-order-{order.id}-payout",
        )

        order.status = "paid"
        order.stripe_transfer_id = transfer.id
        order.buyer_confirmed_at = utc_now()

        if order.trip_id is not None:
            trip = db.query(Trip).filter(
                Trip.id == order.trip_id
            ).first()

            if trip:
                trip.total_earned = (
                    (trip.total_earned or 0)
                    + (amount / 100)
                )

        db.add(
            OrderEvent(
                order_id=order.id,
                event_type="buyer_confirmed",
                description=(
                    f"Buyer confirmed Walmart delivery. "
                    f"Stripe transfer {transfer.id} created."
                ),
                created_at=utc_now(),
            )
        )

        db.commit()
        db.refresh(order)

    except stripe.error.StripeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Stripe could not process the traveler payout.",
        ) from exc

    except Exception:
        db.rollback()
        raise

    return {
        "status": "success",
        "order_id": order.id,
        "order_status": order.status,
        "transfer_id": transfer.id,
        "amount_cents": amount,
        "amount_usd": round(amount / 100, 2),
    }


# --------------------------------------------------
# Get Walmart Order Status
# --------------------------------------------------
@router.get("/{order_id}/status")
def get_order_status(
    order_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    user = get_current_user(db, token)

    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if user.id not in (order.buyer_id, order.traveler_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this order.",
        )

    return {
        "order_id": order.id,
        "merchant": order.merchant_name,
        "status": order.status,
        "weight_lbs": order.weight_lbs,
        "traveler_fee_cents": order.traveler_fee_cents,
        "delivered_at": (
            order.delivered_at.isoformat()
            if order.delivered_at else None
        ),
        "buyer_confirmed_at": (
            order.buyer_confirmed_at.isoformat()
            if order.buyer_confirmed_at else None
        ),
    }


