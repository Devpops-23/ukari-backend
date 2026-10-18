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
# CREATE CONNECTED ACCOUNT
# ---------------------------------------------------------
@router.post("/stripe/connect/create-account")
@router.post("/stripe/create-account")
def create_connect_account(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if traveler.stripe_account_id:
        return {"message": "Account already exists", "account_id": traveler.stripe_account_id}

    account_id = None
    if stripe.api_key:
        try:
            account = stripe.Account.create(
                type="express",
                email=traveler.email,
                capabilities={"transfers": {"requested": True}},
            )
            account_id = account["id"]
        except Exception as e:
            # Fallback for dev / mock
            account_id = f"acct_mock_{traveler.id}"
    else:
        account_id = f"acct_mock_{traveler.id}"

    traveler.stripe_account_id = account_id
    db.commit()
    db.refresh(traveler)

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
    if not traveler.stripe_account_id:
        if stripe.api_key:
            try:
                account = stripe.Account.create(
                    type="express",
                    email=traveler.email,
                    capabilities={"transfers": {"requested": True}},
                )
                traveler.stripe_account_id = account["id"]
            except Exception:
                traveler.stripe_account_id = f"acct_mock_{traveler.id}"
        else:
            traveler.stripe_account_id = f"acct_mock_{traveler.id}"
        db.commit()
        db.refresh(traveler)

    url = f"https://connect.stripe.com/express/oauth/authorize?response_type=code&client_id=ca_mock&scope=read_write&state={traveler.id}"
    if stripe.api_key and not traveler.stripe_account_id.startswith("acct_mock_"):
        try:
            link = stripe.AccountLink.create(
                account=traveler.stripe_account_id,
                refresh_url="http://localhost:3000/dashboard/payouts",
                return_url="http://localhost:3000/dashboard/payouts?status=success",
                type="account_onboarding",
            )
            url = link["url"]
        except Exception:
            pass

    return {"status": "success", "url": url, "account_id": traveler.stripe_account_id}


# ---------------------------------------------------------
# STATUS (USED BY FRONTEND PAYOUTS: /stripe/status)
# ---------------------------------------------------------
@router.get("/stripe/status")
@router.get("/stripe/connect/status")
def get_stripe_status(
    traveler: User = Depends(get_current_user),
):
    return {
        "status": "active" if traveler.stripe_account_id else "not_connected",
        "account_id": traveler.stripe_account_id or "",
        "charges_enabled": bool(traveler.stripe_account_id),
        "payouts_enabled": bool(traveler.stripe_account_id),
        "details_submitted": bool(traveler.stripe_account_id),
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
    if not traveler.stripe_account_id:
        traveler.stripe_account_id = f"acct_mock_{traveler.id}"
        db.commit()
        db.refresh(traveler)

    url = f"https://connect.stripe.com/express/oauth/authorize?response_type=code&client_id=ca_mock&scope=read_write&state={traveler.id}"
    if stripe.api_key and not traveler.stripe_account_id.startswith("acct_mock_"):
        try:
            link = stripe.AccountLink.create(
                account=traveler.stripe_account_id,
                refresh_url="http://localhost:3000/traveler/onboarding",
                return_url="http://localhost:3000/traveler/onboarding?complete=1",
                type="account_onboarding",
            )
            url = link["url"]
        except Exception:
            pass

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









