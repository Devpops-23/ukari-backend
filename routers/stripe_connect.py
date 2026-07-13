from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
import os

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_current_traveler  # FIXED IMPORT



router = APIRouter(prefix="/stripe/connect", tags=["Stripe Connect"])

# ---------------------------------------------------------
# LOAD STRIPE SECRET KEY (SAFE)
# ---------------------------------------------------------
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")




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


# ---------------------------------------------------------
# CREATE UPDATE LINK (FOR SSN LAST‑4, DOB, ETC.)
# ---------------------------------------------------------
@router.get("/update-link")
def create_update_link(
    traveler: User = Depends(get_current_traveler)
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    try:
        link = stripe.AccountLink.create(
            account=traveler.stripe_account_id,
            refresh_url="https://ukari-backend-api.onrender.com/stripe/connect/refresh",
            return_url="https://ukari-backend-api.onrender.com/stripe/connect/return",
            type="account_update",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"url": link["url"]}


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









