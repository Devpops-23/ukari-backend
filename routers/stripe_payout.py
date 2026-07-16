import os
import stripe
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from db_utils.db import get_db
from utils.auth import get_current_user

router = APIRouter(
    prefix="/stripe/payout",
    tags=["Stripe"]
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_traveler_payout(traveler_stripe_account_id: str, amount_cents: int, order_id: int):
    try:
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="usd",
            destination=traveler_stripe_account_id,
            metadata={"order_id": order_id}
        )
        return transfer
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}")
def payout_traveler(order_id: int, token: str, db: Session = Depends(get_db)):
    """
    Admin-triggered payout to traveler.
    """
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    # Fetch order
    from db_utils.models import Order, User

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    traveler = db.query(User).filter(User.id == order.traveler_id).first()
    if not traveler or not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe account")

    # Perform payout
    transfer = create_traveler_payout(
        traveler_stripe_account_id=traveler.stripe_account_id,
        amount_cents=order.item_price_cents,
        order_id=order.id
    )

    return {
        "status": "success",
        "transfer": transfer
    }










