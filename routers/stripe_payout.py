# routers/stripe_payout.py

import os
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, OrderEvent
from auth.auth_router import get_current_traveler  # correct JWT auth

# Load Stripe Secret Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(
    prefix="/stripe/payout",
    tags=["Stripe Payout"],
)


# ---------------------------------------------------------
# Helper: Log payout events
# ---------------------------------------------------------
def log_event(db: Session, user_id: int, amount: int):
    event = OrderEvent(
        order_id=None,
        event_type="traveler_payout",
        message=f"Traveler {user_id} requested payout of {amount} cents",
    )
    db.add(event)
    db.commit()


# ---------------------------------------------------------
# TRAVELER: REQUEST PAYOUT OF AVAILABLE BALANCE
# ---------------------------------------------------------
@router.post("/")
def create_payout(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_traveler(token=token, db=db)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can request payouts")

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe connected account")

    # Stripe account must be fully enabled
    if not user.stripe_charges_enabled or not user.stripe_payouts_enabled:
        raise HTTPException(
            status_code=400,
            detail="Stripe account is not fully enabled for payouts"
        )

    # Retrieve balance
    try:
        balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    # Filter USD available balance
    available = [b for b in balance["available"] if b["currency"] == "usd"]

    if not available:
        raise HTTPException(status_code=400, detail="No USD balance available")

    amount = available[0]["amount"]

    if amount <= 0:
        raise HTTPException(status_code=400, detail="No available balance to pay out")

    # Stripe Connect Transfer (correct method)
    try:
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="usd",
            destination=user.stripe_account_id,
            metadata={"traveler_id": user.id},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payout failed: {str(e)}")

    # Log event
    log_event(db, user.id, amount)

    return {
        "status": "success",
        "amount": amount,
        "currency": "usd",
        "transfer_id": transfer["id"],
        "created_at": datetime.utcnow().isoformat(),
    }



