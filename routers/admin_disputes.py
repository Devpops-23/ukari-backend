from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_utils.database import get_db
from db_utils.models import Order, Trip
from utils.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin Disputes"])


# ---------------------------------------------------------
# ADMIN AUTH CHECK
# ---------------------------------------------------------
def require_admin(user):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------
# 1. GET ALL DISPUTED ORDERS
# ---------------------------------------------------------
@router.get("/disputes")
def get_disputes(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    disputes = (
        db.query(Order)
        .filter(Order.status == "disputed")
        .order_by(Order.dispute_created_at.desc())
        .all()
    )

    formatted = []
    for d in disputes:
        formatted.append({
            "order_id": d.id,
            "amount": d.amount,
            "buyer_name": f"User {d.buyer_id}",
            "traveler_name": f"User {d.traveler_id}",
            "dispute_reason": d.dispute_reason,
            "dispute_status": d.dispute_status,
            "created_at": d.dispute_created_at.isoformat() if d.dispute_created_at else None
        })

    return {"status": "success", "disputes": formatted}


# ---------------------------------------------------------
# 2. RESOLVE DISPUTE IN FAVOR OF TRAVELER
# ---------------------------------------------------------
@router.post("/disputes/{order_id}/resolve")
def resolve_dispute(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="Order is not disputed")

    # Mark dispute resolved
    order.dispute_status = "resolved"
    order.status = "buyer_confirmed"  # allow payout
    order.buyer_confirmed_at = datetime.utcnow()

    # Add earnings to trip
    if order.trip_id:
        trip = db.query(Trip).filter(Trip.id == order.trip_id).first()
        if trip:
            trip.total_earned += order.amount

    db.commit()

    return {"status": "success", "message": "Dispute resolved in favor of traveler"}


# ---------------------------------------------------------
# 3. REFUND BUYER (Admin decision)
# ---------------------------------------------------------
@router.post("/disputes/{order_id}/refund")
def refund_buyer(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    require_admin(user)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="Order is not disputed")

    # Mark dispute resolved
    order.dispute_status = "resolved"
    order.status = "refunded"
    order.paid_at = datetime.utcnow()

    # Remove earnings from trip if previously added
    if order.trip_id:
        trip = db.query(Trip).filter(Trip.id == order.trip_id).first()
        if trip:
            trip.total_earned -= order.amount
            if trip.total_earned < 0:
                trip.total_earned = 0

    db.commit()

    return {"status": "success", "message": "Buyer refunded successfully"}
