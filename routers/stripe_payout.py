import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import get_db
from models import Traveler

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(prefix="/stripe", tags=["Stripe Payouts"])


def get_current_user(db: Session, token: str):
    user = db.query(Traveler).filter(Traveler.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.post("/payout")
def create_payout(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Stripe account not connected")

    # Fetch balance
    balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)
    available = balance["available"][0]["amount"]

    if available <= 0:
        raise HTTPException(status_code=400, detail="No available balance to withdraw")

    # Create payout
    payout = stripe.Payout.create(
        amount=available,
        currency=balance["available"][0]["currency"],
        stripe_account=user.stripe_account_id,
    )

    return {
        "status": "success",
        "payout_id": payout["id"],
        "amount": available / 100,
    }
