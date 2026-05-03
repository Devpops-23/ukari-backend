from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user


router = APIRouter(prefix="/realtime", tags=["Real-Time Matching"])


# ---------------------------------------------------------
# INTERNAL: SEND NOTIFICATION TO TRAVELER
# (Replace with Firebase/APNs/SMS later)
# ---------------------------------------------------------
def send_notification(traveler: User, payload: dict):
    """
    Placeholder notification system.
    Replace with Firebase, APNs, SMS, or email later.
    """
    print(f"[NOTIFY] Traveler {traveler.id} -> {payload}")


# ---------------------------------------------------------
# REAL-TIME MATCHING TRIGGERED WHEN A NEW ORDER IS CREATED
# ---------------------------------------------------------
@router.post("/order-created/{order_id}")
def order_created_event(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Fetch all active trips going to the same destination
    trips = (
        db.query(Trip)
        .filter(
            Trip.destination == order.delivery_location,
            Trip.status == "active"
        )
        .all()
    )

    if not trips:
        return {"status": "success", "message": "No matching trips found"}

    # Evaluate each trip
    for trip in trips:

        # Weight check (placeholder: using item_price as weight)
        if (order.item_price or 0) > (trip.max_weight or 9999):
            continue

        # Calculate match score
        age_minutes = (datetime.utcnow() - order.created_at).total_seconds() / 60
        urgency_score = min(age_minutes / 60, 1.0)
        earnings_score = (order.traveler_fee or 0) / 50
        weight_score = 1.0

        final_score = (weight_score * 0.5) + (urgency_score * 0.2) + (earnings_score * 0.3)

        # Notify traveler
        traveler = db.query(User).filter(User.id == trip.traveler_id).first()

        if traveler:
            send_notification(
                traveler,
                {
                    "type": "new_order_match",
                    "order_id": order.id,
                    "destination": order.delivery_location,
                    "weight": order.item_price,
                    "traveler_fee": order.traveler_fee,
                    "score": round(final_score, 4),
                }
            )

    return {
        "status": "success",
        "message": "Real-time matching executed",
        "order_id": order.id,
        "matched_trips": len(trips),
    }
