from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from auth.jwt_handler import decode_token
from config import stripe
from . import payouts_internal

router = APIRouter(
    prefix="/internal/payouts",
    tags=["Internal Payouts"],
)


def get_user_from_token(db: Session, token: str) -> User:
    """Decode JWT and return the authenticated user."""
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ---------------------------------------------------------
# INSTANT PAYOUT (INTERNAL ONLY)
# ---------------------------------------------------------
@router.post("/instant", include_in_schema=False)
def instant_payout(token: str, db: Session = Depends(get_db)):
    user = get_user_from_token(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can cash out")

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    # Get available balance on the connected account
    balance = stripe.Balance.retrieve(stripe_account=user.stripe_account_id)

    available = [
        b for b in balance["available"] if b["currency"] == "usd"
    ]
    if not available or available[0]["amount"] <= 0:
        raise HTTPException(status_code=400, detail="No available balance to cash out")

    amount = available[0]["amount"]  # in cents

    # Trigger instant payout
    try:
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
            method="instant",
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


# ---------------------------------------------------------
# PAYOUT HISTORY (INTERNAL ONLY)
# ---------------------------------------------------------
@router.get("/history", include_in_schema=False)
def payout_history(token: str, db: Session = Depends(get_db)):
    """
    Internal-only endpoint.
    Returns the last 50 payouts from the traveler's Stripe account.
    """
    user = get_user_from_token(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view payout history")

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    # Retrieve payouts from Stripe
    payouts = stripe.Payout.list(
        limit=50,
        stripe_account=user.stripe_account_id
    )

    history = []
    for p in payouts.data:
        history.append({
            "id": p.id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,  # paid, pending, in_transit, canceled, failed
            "arrival_date": p.arrival_date,
            "created": p.created,
            "method": p.method,  # instant or standard
        })

    return {"payouts": history}

