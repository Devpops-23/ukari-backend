# routers/stripe_webhook.py

import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils.db import get_db
from db_utils.models import Order, User
from utils.event_logger import log_event

router = APIRouter(
    prefix="/stripe",
    tags=["Stripe Webhooks"],
)

# Load keys
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature error: {str(e)}")

    event_type = event["type"]
    data = event["data"]["object"]

    # ---------------------------------------------------------
    # 1. PAYMENT SUCCESS (buyer charged)
    # ---------------------------------------------------------
    if event_type == "payment_intent.succeeded":
        order_id = data["metadata"].get("ukari_order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = "paid_platform"
                db.commit()

                log_event(
                    db=db,
                    order_id=order.id,
                    event_type="payment_succeeded",
                    description="Buyer payment succeeded",
                )

    # ---------------------------------------------------------
    # 2. ACCOUNT UPDATED (traveler onboarding)
    # ---------------------------------------------------------
    if event_type == "account.updated":
        account_id = data["id"]

        traveler = db.query(User).filter(User.stripe_account_id == account_id).first()
        if traveler:
            traveler.stripe_charges_enabled = data.get("charges_enabled", False)
            traveler.stripe_payouts_enabled = data.get("payouts_enabled", False)
            traveler.account_verified = data.get("details_submitted", False)
            db.commit()

            log_event(
                db=db,
                order_id=None,
                event_type="account_updated",
                description=f"Traveler {traveler.id} Stripe account updated",
            )

    # ---------------------------------------------------------
    # 3. CHARGEBACK
    # ---------------------------------------------------------
    if event_type == "charge.dispute.created":
        order_id = data["metadata"].get("ukari_order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                buyer = db.query(User).filter(User.id == order.buyer_id).first()
                if buyer:
                    buyer.chargeback_count += 1
                    db.commit()

                order.status = "disputed"
                db.commit()

                log_event(
                    db=db,
                    order_id=order.id,
                    event_type="chargeback",
                    description="Stripe dispute opened by buyer",
                )

    # ---------------------------------------------------------
    # 4. REFUND
    # ---------------------------------------------------------
    if event_type == "charge.refunded":
        order_id = data["metadata"].get("ukari_order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = "refunded"
                db.commit()

                log_event(
                    db=db,
                    order_id=order.id,
                    event_type="refund",
                    description="Stripe refund processed",
                )

    # ---------------------------------------------------------
    # 5. PAYOUT SUCCESS (Stripe → traveler bank)
    # ---------------------------------------------------------
    if event_type == "payout.paid":
        account_id = data["destination"]
        traveler = db.query(User).filter(User.stripe_account_id == account_id).first()

        if traveler:
            log_event(
                db=db,
                order_id=None,
                event_type="payout_paid",
                description=f"Payout sent to traveler {traveler.id}",
            )

    return {"status": "success"}


