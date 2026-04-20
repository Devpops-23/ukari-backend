from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils.db import get_db
from db_utils.models import Trip, Order
from utils.auth import get_current_user

router = APIRouter(prefix="/trips", tags=["Trips"])


# ---------------------------------------------------------
# TRAVELER CREATES A TRIP
# ---------------------------------------------------------
@router.post("/create")
def create_trip(
    origin: str,
    destination: str,
    travel_date: str,
    max_weight: float,
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can create trips")

    trip = Trip(
        traveler_id=user.id,
        origin=origin,
        destination=destination,
        travel_date=datetime.fromisoformat(travel_date),
        status="active",
        total_earned=0.0,
    )

    # Store max weight capacity in Trip (new field)
    trip.max_weight = max_weight

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return {
        "status": "success",
        "message": "Trip created",
        "trip_id": trip.id,
        "origin": origin,
        "destination": destination,
        "travel_date": travel_date,
        "max_weight": max_weight,
    }


# ---------------------------------------------------------
# MATCH ORDERS TO TRIP BASED ON DESTINATION + WEIGHT
# ---------------------------------------------------------
@router.get("/{trip_id}/matches")
def get_trip_matches(trip_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view matches")

    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.traveler_id == user.id)
        .first()
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or unauthorized")

    # Find orders going to the same destination AND within weight limit
    orders = (
        db.query(Order)
        .filter(
            Order.status == "pending",
            Order.delivery_location == trip.destination,
            Order.item_price <= trip.max_weight  # assuming item_price = weight for now
        )
        .order_by(Order.id.desc())
        .all()
    )

    formatted = []
    for o in orders:
        formatted.append({
            "order_id": o.id,
            "item_name": o.item_name,
            "weight": o.item_price,  # replace with actual weight field later
            "destination": o.delivery_location,
            "amount": o.amount,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return {
        "status": "success",
        "trip_id": trip.id,
        "origin": trip.origin,
        "destination": trip.destination,
        "max_weight": trip.max_weight,
        "matches": formatted,
    }
