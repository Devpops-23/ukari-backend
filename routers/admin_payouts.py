from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils.db import get_db
from db_utils.models import User, Order
from utils.auth import get_current_user

router = APIRouter()

# ---------------------------------------------------------
# U-KARI FEE ENGINE (FLAT FEES)
# ---------------------------------------------------------

PLATFORM_FEE = 10.0
TRAVELER_FEE = 25.0

def calculate_fees(item_price: float):
    platform_fee = PLATFORM_FEE
    traveler_fee = TRAVELER_FEE
    total_charged = item_price + platform_fee + traveler_fee

    return {
        "platform_fee": platform_fee,
        "traveler_fee": traveler_fee,
        "total_charged": total_charged
    }


# ---------------------------------------------------------
# ADMIN AUTH CHECK
# ---------------------------------------------------------
def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------
# 1. GET ALL PAYOUTS (Grouped by traveler)
# ---------------------------------------------------------
@router.get("/payouts")
def get_all_payouts(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    orders = (
        db.query(Order)
        .filter(Order.status.in_(["buyer_confirmed", "paid", "refunded", "frozen"]))
        .order_by(Order.id.desc())
        .all()
    )

    payouts = {}

    for o in orders:
        if not o.traveler_id:
            continue

        traveler = db.query(User).filter(User.id == o.traveler_id).first()

        if o.traveler_id not in payouts:
            payouts[o.traveler_id] = {
                "traveler_id": o.traveler_id,
                "traveler_name": traveler.email if traveler else "Unknown",
                "amount": 0.0,
                "status": "pending",
                "stripe_transfer_id": None,
                "orders": []
            }

        payouts[o.traveler_id]["orders"].append({
            "order_id": o.id,
            "traveler_fee": o.traveler_fee
        })

        payouts[o.traveler_id]["amount"] += o.traveler_fee

        if o.stripe_transfer_id:
            payouts[o.traveler_id]["stripe_transfer_id"] = o.stripe_transfer_id
            payouts[o.traveler_id]["status"] = "paid"

        if o.status in ["refunded", "frozen"]:
            payouts[o.traveler_id]["status"] = "frozen"

    return {"status": "success", "payouts": list(payouts.values())}


# ---------------------------------------------------------
# 2. GET SINGLE PAYOUT DETAILS
# ---------------------------------------------------------
@router.get("/payouts/{traveler_id}")
def get_payout_details(traveler_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler_id)
        .filter(Order.status.in_(["buyer_confirmed", "paid", "refunded", "frozen"]))
        .order_by(Order.id.desc())
        .all()


