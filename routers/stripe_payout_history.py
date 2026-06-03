# routers/stripe_payout.py

import os
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_current_user

# Load Stripe Secret Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(tags=["Stripe"])


@router.post("/")
def create_payout(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can request payouts")

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

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

    # Attempt payout
    try:
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
            method="standard",
            stripe_account=user.stripe_account_id,
        )
    except stripe.error.InvalidRequestError as e:
        raise HTTPException(status_code=400, detail=f"Payout failed: {str(e)}")
    except stripe.error.PermissionError:
        raise HTTPException(status_code=403, detail="Stripe account not allowed to receive payouts")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payout failed: {str(e)}")

    return {
        "status": "success",
        "amount": amount,
        "currency": "usd",
        "payout_id": payout.id,
        "payout_created_at": datetime.utcnow().isoformat()
    }


