from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Trip, Order
from auth.auth_router import get_current_traveler
from schemas import TravelerOut, TripOut, OrderOut

router = APIRouter()


# ---------------------------------------------------------
# GET CURRENT TRAVELER PROFILE
# ---------------------------------------------------------
@router.get("/me", response_model=TravelerOut)
def get_my_profile(traveler: User = Depends(get_current_traveler)):
    return traveler


# ---------------------------------------------------------
# GET ALL TRIPS FOR CURRENT TRAVELER
# ---------------------------------------------------------
@router.get("/trips", response_model=list[TripOut])
def get_my_trips(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    trips = db.query(Trip).filter(Trip.traveler_id == traveler.id).all()
    return trips


# ---------------------------------------------------------
# GET ALL ORDERS FOR CURRENT TRAVELER
# ---------------------------------------------------------
@router.get("/orders", response_model=list[OrderOut])
def get_my_orders(
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(Order.traveler_id == traveler.id).all()
    return orders


# ---------------------------------------------------------
# GET A SPECIFIC TRIP
# ---------------------------------------------------------
@router.get("/trips/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: int,
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.traveler_id == traveler.id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return trip


# ---------------------------------------------------------
# GET A SPECIFIC ORDER
# ---------------------------------------------------------
@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    traveler: User = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.traveler_id == traveler




