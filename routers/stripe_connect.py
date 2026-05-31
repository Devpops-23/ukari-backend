from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
import os

from db_utils.db import get_db
from db_utils.models import User
from auth.auth_router import get_current_traveler

router = APIRouter(prefix="/stripe/connect", tags=["Stripe Connect"])

# Load Stripe Secret Key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is not set")

stripe.api_key = STRIPE_SECRET_KEY


# ---------------------------------------------------------
# CREATE CONNECTED ACCOUNT
# ---------------------------------------------------------
@router.post("/create-account")
def create_connect_account(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    if traveler.stripe_account_id:
        return {"message": "Account already exists", "account_id": traveler.stripe_account_id}

    try:
        account = stripe.Account.create(
            type="express",
            email=traveler.email,
            capabilities={"transfers": {"requested": True}},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    traveler.stripe_account_id = account["id"]
    db.commit()
    db.refresh(traveler)

    return {"account_id": account["id"]}


# ---------------------------------------------------------
# CREATE ONBOARDING LINK
# ---------------------------------------------------------
@router.get("/onboarding-link")
def create_onboarding_link(
    traveler: User = Depends(get_current_traveler)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        link = stripe.AccountLink.create(
            account=traveler.stripe_account_id,
            refresh_url="https://ukari-backend-api.onrender.com/stripe/connect/refresh",
            return_url="https://ukari-backend-api.onrender.com/stripe/connect/return",
            type="account_onboarding",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"url": link["url"]}

@router.get("/update-link")
def create_update_link(current_user: User = Depends(get_current_user)):
    account_id = current_user.stripe_account_id

    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url="https://ukari.com/reauth",
        return_url="https://ukari.com/return",
        type="account_update"
    )

    return {"url": link.url}



# ---------------------------------------------------------
# REQUIRED BY STRIPE — REFRESH + RETURN ROUTES
# ---------------------------------------------------------
@router.get("/refresh")
def refresh():
    return {"message": "Onboarding interrupted. Please restart onboarding."}


@router.get("/return")
def return_to_app():
    return {"message": "Onboarding complete. You may return to the app."}


# ---------------------------------------------------------
# ACCOUNT STATUS
# ---------------------------------------------------------
@router.get("/account-status")
def get_account_status(
    traveler: User = Depends(get_current_traveler)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        account = stripe.Account.retrieve(traveler.stripe_account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "charges_enabled": account["charges_enabled"],
        "payouts_enabled": account["payouts_enabled"],
        "details_submitted": account["details_submitted"],
    }








