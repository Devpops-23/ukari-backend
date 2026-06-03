from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe

from db_utils.db import get_db
from db_utils.models import User
from auth.auth_router import get_current_traveler

router = APIRouter(tags=["Stripe"])


@router.post("/")
def create_payout(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    # Traveler must have a connected account
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    # Retrieve balance from Stripe
    try:
        balance = stripe.Balance.retrieve(
            stripe_account=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    # Find available USD balance
    available_usd = next(
        (b for b in balance["available"] if b["currency"] == "usd"),
        None
    )

    if not available_usd or available_usd["amount"] <= 0:
        raise HTTPException(status_code=400, detail="No available balance to pay out")

    amount = available_usd["amount"]

    # Create payout
    try:
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
            method="standard",
            stripe_account=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payout failed: {str(e)}")

    return {
        "status": "success",
        "payout_id": payout.id,
        "amount": amount,
        "currency": "usd"
    }




