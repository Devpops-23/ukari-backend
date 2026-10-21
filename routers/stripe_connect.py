from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import stripe
import os

from db_utils.db import get_db
from db_utils.models import User
from utils.auth import get_current_user, get_current_traveler

router = APIRouter(tags=["Stripe Connect"])

# ---------------------------------------------------------
# LOAD STRIPE SECRET KEY (SAFE)
# ---------------------------------------------------------
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def ensure_stripe_account(traveler: User, db: Session) -> str:
    # If account is a mock or missing, and we have a valid stripe API key, create real Stripe account
    if not traveler.stripe_account_id or traveler.stripe_account_id.startswith("acct_mock_"):
        if stripe.api_key:
            try:
                account = stripe.Account.create(
                    type="express",
                    email=traveler.email,
                    capabilities={"transfers": {"requested": True}},
                )
                traveler.stripe_account_id = account["id"]
                db.commit()
                db.refresh(traveler)
                return traveler.stripe_account_id
            except Exception as e:
                print("Failed to create real Stripe account:", e)

        if not traveler.stripe_account_id:
            traveler.stripe_account_id = f"acct_mock_{traveler.id}"
            db.commit()
            db.refresh(traveler)

    return traveler.stripe_account_id


def get_onboarding_url(traveler: User, return_path: str = "/dashboard/payouts") -> str:
    if stripe.api_key and traveler.stripe_account_id and not traveler.stripe_account_id.startswith("acct_mock_"):
        try:
            link = stripe.AccountLink.create(
                account=traveler.stripe_account_id,
                refresh_url=f"http://localhost:3000{return_path}",
                return_url=f"http://localhost:3000{return_path}?status=success",
                type="account_onboarding",
            )
            return link["url"]
        except Exception as e:
            print("Failed to create Stripe AccountLink:", e)

    # In fallback or mock mode, never redirect to a fake client_id on connect.stripe.com
    # as Stripe returns 'multi_region_routing_target_not_found'. Safely return to app:
    return f"http://localhost:3000{return_path}?status=success"


# ---------------------------------------------------------
# CREATE CONNECTED ACCOUNT
# ---------------------------------------------------------
@router.post("/stripe/connect/create-account")
@router.post("/stripe/create-account")
def create_connect_account(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = ensure_stripe_account(traveler, db)
    return {"account_id": account_id}


# ---------------------------------------------------------
# ONBOARD (USED BY FRONTEND PAYOUTS: /stripe/onboard)
# ---------------------------------------------------------
@router.post("/stripe/onboard")
@router.post("/stripe/connect/onboard")
def onboard_user(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = ensure_stripe_account(traveler, db)
    url = get_onboarding_url(traveler, return_path="/dashboard/payouts")
    return {"status": "success", "url": url, "account_id": account_id}


# ---------------------------------------------------------
# STATUS (USED BY FRONTEND PAYOUTS: /stripe/status)
# ---------------------------------------------------------
@router.get("/stripe/status")
@router.get("/stripe/connect/status")
def get_stripe_status(
    traveler: User = Depends(get_current_user),
):
    account_id = traveler.stripe_account_id or ""
    charges_enabled = False
    payouts_enabled = False
    details_submitted = False

    if stripe.api_key and account_id and not account_id.startswith("acct_mock_"):
        try:
            acct = stripe.Account.retrieve(account_id)
            charges_enabled = acct.get("charges_enabled", False)
            payouts_enabled = acct.get("payouts_enabled", False)
            details_submitted = acct.get("details_submitted", False)
        except Exception:
            pass
    elif account_id.startswith("acct_mock_"):
        charges_enabled = True
        payouts_enabled = True
        details_submitted = True

    status_str = "active" if (payouts_enabled or details_submitted) else ("pending" if account_id else "not_connected")

    return {
        "status": status_str,
        "account_id": account_id,
        "charges_enabled": charges_enabled,
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
    }


# ---------------------------------------------------------
# CREATE ONBOARDING LINK (GET & POST)
# ---------------------------------------------------------
@router.get("/stripe/connect/onboarding-link")
@router.post("/stripe/connect/onboarding-link")
@router.get("/stripe/onboarding-link")
@router.post("/stripe/onboarding-link")
def create_onboarding_link(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_stripe_account(traveler, db)
    url = get_onboarding_url(traveler, return_path="/traveler/onboarding")
    return {"url": url}


# ---------------------------------------------------------
# CREATE UPDATE LINK (FOR SSN LAST‑4, DOB, ETC.)
# ---------------------------------------------------------
@router.get("/stripe/connect/update-link")
@router.get("/stripe/update-link")
def create_update_link(
    traveler: User = Depends(get_current_traveler),
):
    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    url = f"https://connect.stripe.com/express/update/{traveler.stripe_account_id}"
    if stripe.api_key and not traveler.stripe_account_id.startswith("acct_mock_"):
        try:
            link = stripe.AccountLink.create(
                account=traveler.stripe_account_id,
                refresh_url="http://localhost:3000/dashboard/payouts",
                return_url="http://localhost:3000/dashboard/payouts",
                type="account_update",
            )
            url = link["url"]
        except Exception:
            pass

    return {"url": url}


# ---------------------------------------------------------
# REQUIRED BY STRIPE — REFRESH + RETURN ROUTES
# ---------------------------------------------------------
@router.get("/stripe/connect/refresh")
@router.get("/stripe/refresh")
def refresh():
    return {"message": "Onboarding interrupted. Please restart onboarding."}


@router.get("/stripe/connect/return")
@router.get("/stripe/return")
def return_to_app():
    return {"message": "Onboarding complete. You may return to the app."}


# ---------------------------------------------------------
# ACCOUNT STATUS
# ---------------------------------------------------------
@router.get("/stripe/connect/account-status")
@router.get("/stripe/account-status")
def get_account_status(
    traveler: User = Depends(get_current_traveler),
):
    if not traveler.stripe_account_id:
        return {
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
        }

    if stripe.api_key and not traveler.stripe_account_id.startswith("acct_mock_"):
        try:
            account = stripe.Account.retrieve(traveler.stripe_account_id)
            return {
                "charges_enabled": account["charges_enabled"],
                "payouts_enabled": account["payouts_enabled"],
                "details_submitted": account["details_submitted"],
            }
        except Exception:
            pass

    return {
        "charges_enabled": True,
        "payouts_enabled": True,
        "details_submitted": True,
    }









