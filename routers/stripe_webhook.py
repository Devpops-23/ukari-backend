from datetime import datetime
import json
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order
from config import stripe
import os

router = APIRouter(
    prefix="/internal/stripe",
    tags=["Stripe Webhooks"],
    include_in_schema=False
)

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature failed: {str(e)}")

    event_type = event["type"]
    data = event["data"]["object"]

    # ---------------------------------------------------------
    # 1. CONNECT ACCOUNT UPDATES (KYC, verification, etc.)
    # ---------------------------------------------------------
    if event_type == "account.updated":
        account_id = data["id"]
        user = db.query(User).filter(User.stripe_account_id == account_id).first()

        if user:
            # Example: mark account as verified
            if data.get("charges_enabled") and data.get("payouts_enabled"):
                user.account_verified = True
            else:
                user.account_verified = False

            db.commit()

    # ---------------------------------------------------------
    # 2. PAYOUT SUCCEEDED
    # ---------------------------------------------------------
    elif event_type == "payout.paid":
        payout_id = data["id"]
        amount = data["amount"]
        account_id = data["stripe_account"]

        user = db.query(User).filter(User.stripe_account_id == account_id).first()
        if user:
            print(f"Payout {payout_id} succeeded for traveler {user.id}")

    # ---------------------------------------------------------
    # 3. PAYOUT FAILED
    # ---------------------------------------------------------
    elif event_type == "payout.failed":
        payout_id = data["id"]
        account_id = data["stripe_account"]

        user = db.query(User).filter(User.stripe_account_id == account_id).first()
        if user:
            print(f"Payout FAILED for traveler {user.id}")
            # You can notify traveler or flag account

    # ---------------------------------------------------------
    # 4. TRANSFER (EARNINGS) CREATED
    # ---------------------------------------------------------
    elif event_type == "transfer.created":
        transfer = data
        order = db.query(Order).filter(Order.stripe_transfer_id == transfer["id"]).first()

        if order:
            order.paid_at = datetime.utcnow()
            db.commit()

    return {"status": "success"}

buyer.chargeback_count += 1

if buyer.chargeback_count >= 2:
    buyer.status = "banned"
