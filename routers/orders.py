```python
import os
import math
from datetime import datetime, timedelta

import stripe

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from utils.auth import get_current_user


router = APIRouter(
    prefix="/walmart",
    tags=["Walmart Purchasing"]
)


# --------------------------------------------------
# STRIPE CONFIGURATION
# --------------------------------------------------

stripe.api_key = (
    os.getenv("STRIPE_SECRET_KEY")
    or os.getenv("STRIPE_API_KEY")
)


# --------------------------------------------------
# U-KARI BUSINESS RULES
# --------------------------------------------------

PAYMENT_WINDOW_HOURS = 2

PLATFORM_FEE_PER_10_LBS_CENTS = 1000
TRAVELER_FEE_PER_ITEM_CENTS = 2500


def utc_now():
    return datetime.utcnow()


def payment_deadline(order):
    return order.created_at + timedelta(
        hours=PAYMENT_WINDOW_HOURS
    )


def payment_window_expired(order):
    return utc_now() >= payment_deadline(order)


# --------------------------------------------------
# PRICING
# --------------------------------------------------

def calculate_platform_fee(weight_lbs: float) -> int:

    if not math.isfinite(weight_lbs) or weight_lbs <= 0:
        raise HTTPException(
            status_code=400,
            detail="Package weight must be greater than zero."
        )

    return (
        math.ceil(weight_lbs / 10)
        * PLATFORM_FEE_PER_10_LBS_CENTS
    )


def calculate_traveler_fee(item_count: int) -> int:

    if item_count < 1:
        raise HTTPException(
            status_code=400,
            detail="At least one item is required."
        )

    return item_count * TRAVELER_FEE_PER_ITEM_CENTS


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class WalmartPurchaseRequest(BaseModel):

    item_name: str = Field(
        ...,
        min_length=1,
        max_length=255
    )

    item_count: int = Field(
        default=1,
        ge=1
    )

    item_price_cents: int = Field(
        ...,
        gt=0
    )

    weight_lbs: float = Field(
        ...,
        gt=0
    )

    size_description: str | None = None

    restricted_item: bool = False

    traveler_id: int

    trip_id: int


class DeliveryProofRequest(BaseModel):

    proof_photo_url: str = Field(
        ...,
        min_length=5
    )


class BuyerConfirmRequest(BaseModel):

    confirmation: bool = True


# --------------------------------------------------
# ORDER EVENTS
# --------------------------------------------------

def create_order_event(
    db: Session,
    order_id: int,
    event_type: str,
    description: str
):

    event = OrderEvent(
        order_id=order_id,
        event_type=event_type,
        description=description,
        message=description,
        created_at=utc_now()
    )

    db.add(event)


# --------------------------------------------------
# GET ORDER
# --------------------------------------------------

def get_order_or_404(
    db: Session,
    order_id: int
):

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    return order


# --------------------------------------------------
# EXPIRE UNPAID ORDERS
# --------------------------------------------------

def expire_unpaid_orders(
    db: Session,
    trip_id: int | None = None
):
    """
    Expire unpaid orders after two hours.

    Expired orders no longer consume trip capacity.
    """

    query = db.query(Order).filter(
        Order.status == "awaiting_payment"
    )

    if trip_id is not None:
        query = query.filter(
            Order.trip_id == trip_id
        )

    unpaid_orders = query.with_for_update().all()

    now = utc_now()

    for order in unpaid_orders:

        if now < payment_deadline(order):
            continue

        # Attempt to cancel the Stripe PaymentIntent.
        if order.stripe_payment_intent_id and stripe.api_key:

            try:
                intent = stripe.PaymentIntent.retrieve(
                    order.stripe_payment_intent_id
                )

                if intent.status in [
                    "requires_payment_method",
                    "requires_confirmation",
                    "requires_action",
                    "requires_capture"
                ]:
                    stripe.PaymentIntent.cancel(intent.id)

            except stripe.StripeError:
                # Do not keep an expired reservation
                # just because Stripe cancellation failed.
                pass

        order.status = "expired"

        create_order_event(
            db,
            order.id,
            "expired",
            (
                "Order expired because buyer did not "
                "complete payment within two hours. "
                "Traveler capacity has been released."
            )
        )

    db.flush()


# --------------------------------------------------
# CREATE WALMART ORDER
# --------------------------------------------------

@router.post("/create-order")
def create_walmart_order(
    payload: WalmartPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can create orders."
        )

    if payload.restricted_item:
        raise HTTPException(
            status_code=400,
            detail="Restricted items cannot be ordered through U-KARI."
        )

    if not math.isfinite(payload.weight_lbs):
        raise HTTPException(
            status_code=400,
            detail="Invalid package weight."
        )

    try:

        traveler = (
            db.query(User)
            .filter(
                User.id == payload.traveler_id,
                User.role == "traveler",
                User.status == "active"
            )
            .first()
        )

        if not traveler:
            raise HTTPException(
                status_code=404,
                detail="Selected traveler not found or inactive."
            )

        # Lock the trip while calculating capacity.
        trip = (
            db.query(Trip)
            .filter(
                Trip.id == payload.trip_id,
                Trip.traveler_id == traveler.id,
                Trip.status == "active"
            )
            .with_for_update()
            .first()
        )

        if not trip:
            raise HTTPException(
                status_code=400,
                detail="Selected trip not found or inactive."
            )

        if trip.max_weight is None or trip.max_weight <= 0:
            raise HTTPException(
                status_code=400,
                detail="Traveler has not declared carrying capacity."
            )

        # Release expired unpaid reservations first.
        expire_unpaid_orders(
            db,
            trip_id=trip.id
        )

        # Calculate capacity currently being used.
        used_weight = (
            db.query(
                func.coalesce(
                    func.sum(Order.weight_lbs),
                    0.0
                )
            )
            .filter(
                Order.trip_id == trip.id,
                Order.status.notin_([
                    "cancelled",
                    "refunded",
                    "expired"
                ]),
                Order.refunded_at.is_(None)
            )
            .scalar()
            or 0.0
        )

        remaining_capacity = (
            float(trip.max_weight)
            - float(used_weight)
        )

        if payload.weight_lbs > remaining_capacity:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"This trip has only "
                    f"{remaining_capacity:.2f} lbs "
                    f"of carrying capacity remaining."
                )
            )

        platform_fee_cents = calculate_platform_fee(
            payload.weight_lbs
        )

        traveler_fee_cents = calculate_traveler_fee(
            payload.item_count
        )

        total_charged_cents = (
            payload.item_price_cents
            + platform_fee_cents
            + traveler_fee_cents
        )

        order = Order(

            item_name=payload.item_name,

            item_price_cents=payload.item_price_cents,
            platform_fee_cents=platform_fee_cents,
            traveler_fee_cents=traveler_fee_cents,
            total_charged_cents=total_charged_cents,

            item_price=payload.item_price_cents / 100,
            platform_fee=platform_fee_cents / 100,
            traveler_fee=traveler_fee_cents / 100,
            total_charged=total_charged_cents / 100,

            weight_lbs=payload.weight_lbs,

            size_description=(
                payload.size_description or ""
            ),

            restricted_item=False,

            buyer_id=current_user.id,
            traveler_id=traveler.id,
            trip_id=trip.id,

            merchant_name="walmart",
            store_name="walmart",

            # Not yet paid.
            status="awaiting_payment",

            created_at=utc_now()
        )

        db.add(order)
        db.flush()

        create_order_event(
            db,
            order.id,
            "created",
            (
                f"Buyer created order. "
                f"Package weight: {payload.weight_lbs} lbs. "
                f"Payment must be completed within "
                f"{PAYMENT_WINDOW_HOURS} hours."
            )
        )

        db.commit()
        db.refresh(order)

        return {
            "status": "success",
            "order_id": order.id,
            "order_status": order.status,
            "payment_required": True,
            "payment_window_hours": PAYMENT_WINDOW_HOURS,
            "payment_deadline": payment_deadline(order).isoformat(),
            "item_price_cents": order.item_price_cents,
            "platform_fee_cents": order.platform_fee_cents,
            "traveler_fee_cents": order.traveler_fee_cents,
            "total_charged_cents": order.total_charged_cents,
            "package_weight_lbs": order.weight_lbs,
            "remaining_trip_capacity_lbs": round(
                remaining_capacity - payload.weight_lbs,
                2
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create order."
        )


# --------------------------------------------------
# CREATE STRIPE PAYMENT INTENT
# --------------------------------------------------

@router.post("/{order_id}/payment-intent")
def create_payment_intent(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can pay for orders."
        )

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    if order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This is not your order."
        )

    expire_unpaid_orders(
        db,
        trip_id=order.trip_id
    )

    if order.status != "awaiting_payment":
        raise HTTPException(
            status_code=400,
            detail="This order is no longer awaiting payment."
        )

    if payment_window_expired(order):
        order.status = "expired"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Your two-hour payment window has expired."
        )

    if not stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured."
        )

    try:

        # Reuse an existing unpaid PaymentIntent.
        if order.stripe_payment_intent_id:

            existing = stripe.PaymentIntent.retrieve(
                order.stripe_payment_intent_id
            )

            if existing.status not in [
                "canceled",
                "succeeded"
            ]:

                return {
                    "order_id": order.id,
                    "payment_intent_id": existing.id,
                    "client_secret": existing.client_secret,
                    "amount_cents": order.total_charged_cents
                }

        intent = stripe.PaymentIntent.create(

            amount=order.total_charged_cents,

            currency="usd",

            automatic_payment_methods={
                "enabled": True
            },

            metadata={
                "ukari_order_id": str(order.id),
                "buyer_id": str(order.buyer_id),
                "traveler_id": str(order.traveler_id)
            },

            idempotency_key=(
                f"ukari-order-{order.id}-payment"
            )
        )

        order.stripe_payment_intent_id = intent.id

        db.commit()

        return {
            "order_id": order.id,
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            "amount_cents": order.total_charged_cents,
            "currency": "usd"
        }

    except stripe.StripeError:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Unable to create Stripe payment."
        )


# --------------------------------------------------
# CONFIRM BUYER PAYMENT
# --------------------------------------------------

@router.post("/{order_id}/payment-confirm")
def confirm_buyer_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can confirm payment."
        )

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    if order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This is not your order."
        )

    if order.status == "pending":
        return {
            "status": "already_paid",
            "order_id": order.id,
            "order_status": order.status
        }

    if order.status != "awaiting_payment":
        raise HTTPException(
            status_code=400,
            detail="This order cannot be paid."
        )

    if not order.stripe_payment_intent_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe payment has been started."
        )

    if not stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured."
        )

    try:

        intent = stripe.PaymentIntent.retrieve(
            order.stripe_payment_intent_id
        )

        if intent.status != "succeeded":
            raise HTTPException(
                status_code=400,
                detail="Stripe has not confirmed successful payment."
            )

        if int(intent.amount_received) != order.total_charged_cents:
            raise HTTPException(
                status_code=400,
                detail="Payment amount does not match this order."
            )

        if intent.metadata.get("ukari_order_id") != str(order.id):
            raise HTTPException(
                status_code=400,
                detail="Payment does not belong to this order."
            )

        # Verify the actual payment occurred before the deadline.
        charge_id = intent.latest_charge

        if not charge_id:
            raise HTTPException(
                status_code=400,
                detail="Unable to verify payment time."
            )

        charge = stripe.Charge.retrieve(charge_id)

        paid_time = datetime.utcfromtimestamp(
            charge.created
        )

        if paid_time >= payment_deadline(order):

            order.status = "expired"
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment was completed after the two-hour "
                    "reservation expired. Contact U-KARI support."
                )
            )

        order.status = "pending"

        create_order_event(
            db,
            order.id,
            "payment_confirmed",
            (
                "Stripe verified buyer payment. "
                "Order is now available for traveler acceptance."
            )
        )

        db.commit()
        db.refresh(order)

        return {
            "status": "payment_confirmed",
            "order_id": order.id,
            "order_status": order.status,
            "message": (
                "Payment received. Your traveler reservation "
                "is now confirmed."
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except stripe.StripeError:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Unable to verify Stripe payment."
        )


# --------------------------------------------------
# TRAVELER ACCEPTS PAID ORDER
# --------------------------------------------------

@router.post("/{order_id}/accept")
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "traveler":
        raise HTTPException(
            status_code=403,
            detail="Only travelers can accept orders."
        )

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    if order.traveler_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This order belongs to another traveler."
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only paid orders can be accepted."
        )

    order.status = "accepted"
    order.accepted_at = utc_now()

    create_order_event(
        db,
        order.id,
        "accepted",
        f"Traveler {current_user.id} accepted the paid order."
    )

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "order_id": order.id,
        "order_status": order.status
    }


# --------------------------------------------------
# TRAVELER MARKS ORDER DELIVERED
# --------------------------------------------------

@router.post("/{order_id}/deliver")
def mark_delivered(
    order_id: int,
    payload: DeliveryProofRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "traveler":
        raise HTTPException(
            status_code=403,
            detail="Only travelers can mark orders delivered."
        )

    order = get_order_or_404(db, order_id)

    if order.traveler_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This is not your order."
        )

    if order.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail="Only accepted orders can be delivered."
        )

    order.status = "delivered"
    order.delivered_at = utc_now()
    order.proof_photo_url = payload.proof_photo_url

    create_order_event(
        db,
        order.id,
        "delivered",
        (
            "Traveler uploaded delivery proof showing "
            "the item in the recipient's hands."
        )
    )

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "order_id": order.id,
        "order_status": order.status,
        "proof_photo_url": order.proof_photo_url
    }


# --------------------------------------------------
# BUYER CONFIRMS DELIVERY
# --------------------------------------------------

@router.post("/{order_id}/buyer-confirm")
def buyer_confirm_delivery(
    order_id: int,
    body: BuyerConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can confirm delivery."
        )

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    if order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This is not your order."
        )

    if order.status == "paid":
        return {
            "status": "already_paid",
            "order_id": order.id,
            "transfer_id": order.stripe_transfer_id
        }

    if not body.confirmation:
        raise HTTPException(
            status_code=400,
            detail="Buyer confirmation is required."
        )

    if order.status != "delivered":
        raise HTTPException(
            status_code=400,
            detail="Traveler must deliver the order first."
        )

    if not order.proof_photo_url:
        raise HTTPException(
            status_code=400,
            detail="Delivery proof photo is missing."
        )

    # Verify the buyer's original payment is still successful.
    if not order.stripe_payment_intent_id:
        raise HTTPException(
            status_code=400,
            detail="Buyer payment has not been recorded."
        )

    if not stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured."
        )

    try:

        intent = stripe.PaymentIntent.retrieve(
            order.stripe_payment_intent_id
        )

        if intent.status != "succeeded":
            raise HTTPException(
                status_code=400,
                detail="Buyer payment has not cleared."
            )

        if int(intent.amount_received) != order.total_charged_cents:
            raise HTTPException(
                status_code=400,
                detail="Buyer payment amount does not match."
            )

        traveler = (
            db.query(User)
            .filter(User.id == order.traveler_id)
            .first()
        )

        if not traveler:
            raise HTTPException(
                status_code=404,
                detail="Traveler account not found."
            )

        if not traveler.stripe_account_id:
            raise HTTPException(
                status_code=400,
                detail="Traveler has not connected a Stripe account."
            )

        if not traveler.stripe_payouts_enabled:
            raise HTTPException(
                status_code=400,
                detail="Traveler's Stripe account is not enabled for payouts."
            )

        amount = order.traveler_fee_cents

        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Traveler payout amount must be greater than zero."
            )

        transfer = stripe.Transfer.create(

            amount=amount,

            currency="usd",

            destination=traveler.stripe_account_id,

            idempotency_key=(
                f"ukari-order-{order.id}-traveler-payout"
            )
        )

        order.status = "paid"
        order.stripe_transfer_id = transfer.id
        order.buyer_confirmed_at = utc_now()

        if order.trip_id is not None:

            trip = (
                db.query(Trip)
                .filter(Trip.id == order.trip_id)
                .first()
            )

            if trip:
                trip.total_earned = (
                    (trip.total_earned or 0)
                    + (amount / 100)
                )

        create_order_event(
            db,
            order.id,
            "buyer_confirmed",
            (
                f"Buyer confirmed delivery. "
                f"Traveler payout of ${amount / 100:.2f} "
                f"initiated. Transfer ID: {transfer.id}."
            )
        )

        db.commit()
        db.refresh(order)

        return {
            "status": "success",
            "order_id": order.id,
            "order_status": order.status,
            "transfer_id": transfer.id,
            "traveler_payment_cents": amount,
            "traveler_payment_dollars": amount / 100
        }

    except HTTPException:
        db.rollback()
        raise

    except stripe.StripeError:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Stripe transfer failed."
        )


# --------------------------------------------------
# GET ORDER STATUS
# --------------------------------------------------

@router.get("/{order_id}/status")
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    order = get_order_or_404(db, order_id)

    if current_user.id not in [
        order.buyer_id,
        order.traveler_id
    ]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this order."
        )

    if order.status == "awaiting_payment":

        expire_unpaid_orders(
            db,
            trip_id=order.trip_id
        )

        db.commit()
        db.refresh(order)

    return {
        "order_id": order.id,
        "status": order.status,
        "traveler_id": order.traveler_id,
        "trip_id": order.trip_id,
        "weight_lbs": order.weight_lbs,
        "traveler_fee_cents": order.traveler_fee_cents,
        "platform_fee_cents": order.platform_fee_cents,
        "created_at": order.created_at.isoformat(),
        "payment_deadline": payment_deadline(order).isoformat(),
        "proof_photo_url": order.proof_photo_url,
        "stripe_transfer_id": order.stripe_transfer_id
    }






















    
