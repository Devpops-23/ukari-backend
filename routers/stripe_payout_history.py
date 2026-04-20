import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import get_db
from models import Traveler

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(prefix="/stripe", tags=["Stripe Payout History"])


def get_current_user(db: Session, token: str):
    user = db.query(Traveler).filter(Traveler.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/payouts")
def get_payout_history(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if not user.stripe_account_id:
        return []

    payouts = stripe.Payout.list(
        stripe_account=user.stripe_account_id,
        limit=20
    )

    history = []
    for p in payouts.data:
        history.append({
            "id": p.id,
            "amount": p.amount / 100,
            "currency": p.currency,
            "status": p.status,
            "arrival_date": p.arrival_date,
            "created": p.created,
        })

    return history
