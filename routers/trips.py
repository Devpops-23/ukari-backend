from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user



router = APIRouter(
    prefix="/trips",
    tags=["Trips"],
)

@router.post("/create")
def create_trip(
    token: str,
    origin: str,
    destination: str,
    travel_date: str,
    max_weight: float,
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can create trips")

    trip = Trip(
        traveler_id=user.id,
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        max_weight=max_weight,
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return {"status": "success", "trip": trip}


