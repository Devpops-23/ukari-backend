# routers/stripe_payout.py

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_current_user

router = APIRouter(
    prefix="/stripe/payout",
    tags=["Stripe Payout"],
)


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

    try:
        balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    available = [b for b in balance["available"] if b["currency"] == "usd"]
    if not available or available[0]["amount"] <= 0:
        raise HTTPException(status_code=400, detail="No available balance to pay out")

    amount = available[0]["amount"]

    try:
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
            method="standard",
            stripe_account=user.stripe_account_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payout failed: {str(e)}")

    return {
        "status": "success",
        "amount": amount,
        "currency": "usd",
        "payout_id": payout.id,
    }


