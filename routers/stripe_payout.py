from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe

from db_utils.db import get_db
from db_utils.models import User
from auth.auth_router import get_current_traveler

router = APIRouter(prefix="/stripe", tags=["Stripe"])



@router.post("/")
def create_payout(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        balance = stripe.Balance.retrieve(
            stripe_account=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    available_usd = next(
        (b for b in balance["available"] if b["currency"] == "usd"),
        None
    )

    if not available_usd or available_usd["amount"] <= 0:
        raise HTTPException(status_code=400, detail="No available balance to pay out")

    amount = available_usd["amount"]

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


@router.post("/transfer")
def create_transfer(
    amount: int,
    traveler: User = Depends(get_current_traveler)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="usd",
            destination=traveler.stripe_account_id
        )
        return {
            "transfer_id": transfer.id,
            "amount": amount,
            "destination": traveler.stripe_account_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/instant")
def instant_transfer_and_payout(
    amount: int,
    traveler: User = Depends(get_current_traveler)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    # STEP 1 — Transfer from platform → traveler
    try:
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="usd",
            destination=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transfer failed: {str(e)}")

    # STEP 2 — Payout from traveler → bank
    try:
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
            method="standard",
            stripe_account=traveler.stripe_account_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payout failed: {str(e)}")

    return {
        "status": "success",
        "transfer_id": transfer.id,
        "payout_id": payout.id,
        "amount": amount,
        "currency": "usd"
    }






