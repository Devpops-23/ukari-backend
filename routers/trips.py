from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Trip
from utils.auth import get_current_user

router = APIRouter(
    prefix="/trips",
    tags=["Trips"],
)


class CreateTripRequest(BaseModel):
    origin: str
    destination: str
    travel_date: str
    max_weight: float = 20.0


@router.post("/create")
def create_trip(
    body: Optional[CreateTripRequest] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    travel_date: Optional[str] = None,
    max_weight: Optional[float] = 20.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can create trips")

    trip_origin = body.origin if body else origin
    trip_dest = body.destination if body else destination
    trip_date_str = body.travel_date if body else travel_date
    trip_weight = body.max_weight if body else (max_weight or 20.0)

    if not trip_origin or not trip_dest or not trip_date_str:
        raise HTTPException(
            status_code=400,
            detail="origin, destination, and travel_date are required",
        )

    parsed_date = None
    try:
        parsed_date = datetime.fromisoformat(trip_date_str.replace("Z", "+00:00"))
    except Exception:
        try:
            parsed_date = datetime.strptime(trip_date_str, "%Y-%m-%d")
        except Exception:
            parsed_date = datetime.utcnow()

    trip = Trip(
        traveler_id=user.id,
        origin=trip_origin,
        destination=trip_dest,
        departure_date=parsed_date,
        arrival_date=parsed_date,
        travel_date=parsed_date,
        max_weight=trip_weight,
        status="active",
        total_earned=0.0,
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return {
        "status": "success",
        "trip": {
            "id": trip.id,
            "origin": trip.origin,
            "destination": trip.destination,
            "departure_date": trip.departure_date.isoformat() if trip.departure_date else None,
            "max_weight": trip.max_weight,
            "status": trip.status,
        },
    }
