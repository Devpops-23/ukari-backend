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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "traveler" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only travelers can view trip earnings")

    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if user.role != "admin" and trip.traveler_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip's earnings")

    orders = db.query(Order).filter(Order.trip_id == trip.id).all()

    total_earned = 0.0
    formatted_orders = []

    for o in orders:
        earned = o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee)
        if o.status in ["delivered", "buyer_confirmed", "paid"]:
            total_earned += earned

        formatted_orders.append({
            "order_id": o.id,
            "item_name": o.item_name,
            "amount_earned": earned,
            "status": o.status,
        })

    return {
        "trip_id": trip.id,
        "total_earned": total_earned,
        "orders": formatted_orders,
    }
