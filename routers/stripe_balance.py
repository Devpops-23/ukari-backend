# routers/stripe_balance.py

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_current_user

router = APIRouter(
    prefix="/stripe/balance",
    tags=["Stripe Balance"],
)


@router.get("/")
def get_balance(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view Stripe balance")

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    return {
        "available": balance["available"],
        "pending": balance["pending"],
    }

