import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import get_db
from models import Traveler

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(prefix="/stripe", tags=["Stripe Balance"])


def get_current_user(db: Session, token: str):
    user = db.query(Traveler).filter(Traveler.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/balance")
def get_balance(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if not user.stripe_account_id:
        return {
            "available": 0,
            "pending": 0,
            "currency": "usd",
        }

    balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)

    available = balance["available"][0]["amount"] / 100
    pending = balance["pending"][0]["amount"] / 100
    currency = balance["available"][0]["currency"]

    return {
        "available": available,
        "pending": pending,
        "currency": currency,
    }
