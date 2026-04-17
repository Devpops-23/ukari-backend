from fastapi import APIRouter

router = APIRouter()

@router.get("/stripe-test")
def stripe_test():
    return {"status": "stripe router is working"}
import os
import stripe
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
from database.db import save_stripe_account, get_traveler_by_id

load_dotenv()

router = APIRouter(prefix="/stripe", tags=["Stripe Connect"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


@router.post("/create-connect-account")
def create_connect_account(data: dict):
    traveler_id = data.get("traveler_id")
    email = data.get("email")

    if not traveler_id or not email:
        raise HTTPException(status_code=400, detail="Missing traveler_id or email")

    # 1. Create Stripe Express account
    account = stripe.Account.create(
        type="express",
        country="US",
        email=email,
        capabilities={"transfers": {"requested": True}},
    )

    # 2. Save account.id in your database
    save_stripe_account(traveler_id, account.id)

    # 3. Return account ID
    return {"account_id": account.id}


@router.post("/onboarding-link")
def onboarding_link(data: dict):
    account_id = data.get("account_id")

    if not account_id:
        raise HTTPException(status_code=400, detail="Missing account_id")

    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url="https://u-kari.com/onboarding/refresh",
        return_url="https://u-kari.com/onboarding/complete",
        type="account_onboarding",
    )

    return {"url": link.url}
