from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order
from utils.auth import get_current_user

router = APIRouter(tags=["Admin Payouts"])


def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------
# 1. GET ALL PAYOUTS
# ---------------------------------------------------------
@router.get("/payouts")
def get_all_payouts(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.status.in_(["buyer_confirmed", "paid", "refunded", "delivered"]))
        .order_by(Order.id.desc())
        .all()
    )

    payouts = []
    for o in orders:
        earned = o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee)
        payouts.append({
            "order_id": o.id,
            "traveler_id": o.traveler_id,
            "buyer_id": o.buyer_id,
            "amount": earned,
            "status": o.status,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "transfer_id": o.stripe_transfer_id,
        })

    return {"status": "success", "payouts": payouts}


@router.get("/payouts/{traveler_id}")
def get_traveler_payout_history(
    traveler_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler_id)
        .order_by(Order.id.desc())
        .all()
    )

    return {
        "status": "success",
        "traveler_id": traveler_id,
        "payouts": [
            {
                "order_id": o.id,
                "amount": o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee),
                "status": o.status,
                "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            }
            for o in orders
        ],
    }
