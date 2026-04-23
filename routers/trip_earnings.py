# routers/trip_earnings.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Trip, Order
from utils.auth import get_current_user

router = APIRouter(
    prefix="/trip-earnings",
    tags=["Trip Earnings"],
)


@router.get("/{trip_id}")
def get_trip_earnings(
    trip_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view trip earnings")

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.traveler_id == user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    orders = db.query(Order).filter(Order.trip_id == trip.id).all()

    total_earned = sum(o.amount_earned for o in orders if o.amount_earned)

    return {
        "trip_id": trip.id,
        "total_earned": total_earned,
        "orders": [
            {
                "order_id": o.id,
                "amount_earned": o.amount_earned,
                "status": o.status,
            }
            for o in orders
        ],
    }
