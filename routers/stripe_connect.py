import stripe
from config import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user

router = APIRouter()


router = APIRouter(
    prefix="/stripe/connect",
    tags=["Stripe Connect"],
)


# ---------------------------------------------------------
# CREATE STRIPE CONNECT ACCOUNT FOR TRAVELER
# ---------------------------------------------------------
@router.post("/create-account")
def create_connect_account(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can create Stripe accounts")

    try:
        account = stripe.Account.create(
            type="express",
            country="US",
            email=user.email,
            capabilities={
                "transfers": {"requested": True},
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    user.stripe_account_id = account.id
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "account_id": account.id,
    }


# ---------------------------------------------------------
# GENERATE ONBOARDING LINK
# ---------------------------------------------------------
@router.get("/onboarding-link")
def get_onboarding_link(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        link = stripe.AccountLink.create(
            account=user.stripe_account_id,
            refresh_url="https://ukari.app/stripe/refresh",
            return_url="https://ukari.app/stripe/return",
            type="account_onboarding",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    return {"url": link.url}


# ---------------------------------------------------------
# CHECK ACCOUNT STATUS
# ---------------------------------------------------------
@router.get("/status")
def get_connect_status(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if not user.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        account = stripe.Account.retrieve(user.stripe_account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    return {
        "charges_enabled": account.charges_enabled,
        "payouts_enabled": account.payouts_enabled,
        "details_submitted": account.details_submitted,
    }




