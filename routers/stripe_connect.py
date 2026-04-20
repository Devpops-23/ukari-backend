from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User
from auth.jwt_handler import decode_token
from config import stripe

router = APIRouter(prefix="/stripe", tags=["Stripe Connect"])


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


@router.post("/connect-link")
def create_connect_link(token: str, db: Session = Depends(get_db)):
    user = get_user_from_token(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can onboard")

    # Create Stripe account if missing
    if not user.stripe_account_id:
        account = stripe.Account.create(
            type="express",
            country="US",
            email=user.email,
            capabilities={"transfers": {"requested": True}},
        )
        user.stripe_account_id = account.id
        db.commit()

    # Create onboarding link
    link = stripe.AccountLink.create(
        account=user.stripe_account_id,
        refresh_url="https://yourapp.com/onboarding/refresh",
        return_url="https://yourapp.com/onboarding/complete",
        type="account_onboarding",
    )

    return {"url": link.url}



