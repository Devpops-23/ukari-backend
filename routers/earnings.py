from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_utils.database import get_db
from db_utils.models import Trip, Order
from utils.auth import get_current_user

router = APIRouter(prefix="/earnings", tags=["Earnings"])


# ---------------------------------------------------------
# 1. EARNINGS SUMMARY (Traveler Dashboard)
# ---------------------------------------------------------
@router.get("/summary")
def earnings_summary(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role not in ["traveler", "admin"]:
        raise HTTPException(status_code=403, detail="Traveler access required")

    orders = (
        db.query(Order)
        .filter(Order.traveler_id == user.id)
        .order_by(Order.id.desc())
        .all()
    )

    total_earned = 0.0
    pending_earnings = 0.0
    available_earnings = 0.0
    recent_orders = []

    for o in orders:
        if o.status in ["buyer_confirmed", "paid"]:
            total_earned += o.amount
            available_earnings += o.amount

        if o.status == "delivered":
            pending_earnings += o.amount

        recent_orders.append({
            "order_id": o.id,
            "amount": o.amount,
            "status": o.status
        })

    recent_orders = recent_orders[:5]

    return {
        "status": "success",
        "total_earned": total_earned,
        "pending_earnings": pending_earnings,
        "available_earnings": available_earnings,
        "recent_orders": recent_orders
    }


# ---------------------------------------------------------
# 2. TRIP EARNINGS BREAKDOWN
# ---------------------------------------------------------
@router.get("/trips")
def get_trip_earnings(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role not in ["traveler", "admin"]:
        raise HTTPException(status_code=403, detail="Traveler access required")

    trips = db.query(Trip).filter(Trip.traveler_id == user.id).all()

    total = 0
    pending = 0
    completed = 0
    trip_list = []

    for trip in trips:
        orders = db.query(Order).filter(Order.trip_id == trip.id).all()

        trip_total = sum(o.amount for o in orders if o.status in ["buyer_confirmed", "paid"])
        trip_pending = sum(o.amount for o in orders if o.status == "delivered")
        trip_completed = sum(o.amount for o in orders if o.status == "paid")

        total += trip_total
        pending += trip_pending
        completed += trip_completed

        trip_list.append({
            "trip_id": trip.id,
            "origin": trip.origin,
            "destination": trip.destination,
            "date": trip.travel_date,
            "status": trip.status,
            "total_earned": trip_total,
            "orders": [
                {
                    "order_id": o.id,
                    "amount": o.amount,
                    "status": o.status
                }
                for o in orders
            ]
        })

    return {
        "status": "success",
        "total": total,
        "pending": pending,
        "completed": completed,
        "trips": trip_list
    }

