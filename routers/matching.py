from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user





router = APIRouter(prefix="/matching", tags=["AI Matching"])


# ---------------------------------------------------------
# AI MATCHING HUB — RECOMMEND BEST ORDERS FOR A TRIP
# ---------------------------------------------------------
@router.get("/recommend/{trip_id}")
def recommend_orders_for_trip(trip_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can receive recommendations")

    # Fetch trip
    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.traveler_id == user.id)
        .first()
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or unauthorized")

    if trip.status != "active":
        raise HTTPException(status_code=400, detail="Cannot recommend orders for inactive trips")

    # Fetch all pending orders going to the same destination
    orders = (
        db.query(Order)
        .filter(
            Order.status == "pending",
            Order.delivery_location == trip.destination
        )
        .all()
    )

    # AI scoring system
    recommendations = []
    for o in orders:

        # Weight match (placeholder: using item_price as weight)
        weight_score = 1.0 if (o.item_price or 0) <= (trip.max_weight or 9999) else 0.0

        # Urgency score (older orders get priority)
        age_minutes = (datetime.utcnow() - o.created_at).total_seconds() / 60
        urgency_score = min(age_minutes / 60, 1.0)  # max 1.0

        # Earnings score
        earnings_score = (o.traveler_fee or 0) / 50  # normalize

        # Final AI score
        final_score = (weight_score * 0.5) + (urgency_score * 0.2) + (earnings_score * 0.3)

        recommendations.append({
            "order_id": o.id,
            "item_name": o.item_name,
            "weight": o.item_price,
            "destination": o.delivery_location,
            "traveler_fee": o.traveler_fee,
            "created_at": o.created_at.isoformat(),
            "score": round(final_score, 4),
        })

    # Sort by score descending
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "status": "success",
        "trip_id": trip.id,
        "origin": trip.origin,
        "destination": trip.destination,
        "max_weight": trip.max_weight,
        "recommended_orders": recommendations,
    }
