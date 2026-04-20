from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_utils.database import get_db
from db_utils.models import Order, Trip
from utils.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin Payouts"])


# ---------------------------------------------------------
# ADMIN AUTH CHECK
# ---------------------------------------------------------
def require_admin(user):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------
# 1. GET ALL PAYOUTS (Grouped by traveler)
# ---------------------------------------------------------
@router.get("/payouts")
def get_all_payouts(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    # Fetch all orders that have been confirmed or paid
    orders = (
        db.query(Order)
        .filter(Order.status.in_(["buyer_confirmed", "paid", "refunded"]))
        .order_by(Order.id.desc())
        .all()
    )

    payouts = {}
    for o in orders:
        traveler_id = o.traveler_id or 0

        if traveler_id not in payouts:
            payouts[traveler_id] = {
                "payout_id": traveler_id,
                "traveler_name": f"User {traveler_id}",
                "amount": 0.0,
                "status": "pending",
                "stripe_transfer_id": None,
                "orders": []
            }

        payouts[traveler_id]["orders"].append({
            "order_id": o.id,
            "amount": o.amount
        })

        payouts[traveler_id]["amount"] += o.amount

        # If any order has a Stripe transfer ID, attach it
        if o.stripe_transfer_id:
            payouts[traveler_id]["stripe_transfer_id"] = o.stripe_transfer_id
            payouts[traveler_id]["status"] = "paid"

        if o.status == "refunded":
            payouts[traveler_id]["status"] = "frozen"

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
        .filter(Order.status.in_(["buyer_confirmed", "paid", "refunded"]))
        .all()
    )

    if not orders:
        raise HTTPException(status_code=404, detail="No payout found for traveler")

    payout = {
        "payout_id": traveler_id,
        "traveler_name": f"User {traveler_id}",
        "amount": sum(o.amount for o in orders),
        "status": "pending",
        "stripe_transfer_id": None,
        "orders": [{"order_id": o.id, "amount": o.amount} for o in orders]
    }

    for o in orders:
        if o.stripe_transfer_id:
            payout["stripe_transfer_id"] = o.stripe_transfer_id
            payout["status"] = "paid"

        if o.status == "refunded":
            payout["status"] = "frozen"

    return {"status": "success", "payout": payout}


# ---------------------------------------------------------
# 3. APPROVE PAYOUT (Admin manually approves)
# ---------------------------------------------------------
@router.post("/payouts/{traveler_id}/approve")
def approve_payout(traveler_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler_id)
        .filter(Order.status == "buyer_confirmed")
        .all()
    )

    if not orders:
        raise HTTPException(status_code=404, detail="No payout available to approve")

    # Mark orders as paid
    for o in orders:
        o.status = "paid"
        o.paid_at = datetime.utcnow()

    db.commit()

    return {"status": "success", "message": "Payout approved and marked as paid"}


# ---------------------------------------------------------
# 4. FREEZE PAYOUT (Admin freezes due to dispute)
# ---------------------------------------------------------
@router.post("/payouts/{traveler_id}/freeze")
def freeze_payout(traveler_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler_id)
        .filter(Order.status.in_(["buyer_confirmed", "delivered"]))
        .all()
    )

    if not orders:
        raise HTTPException(status_code=404, detail="No payout available to freeze")

    for o in orders:
        o.status = "frozen"

    db.commit()

    return {"status": "success", "message": "Payout frozen due to dispute or admin action"}
