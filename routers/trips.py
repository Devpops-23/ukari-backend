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
    origin: Optional[str] = None
    destination: Optional[str] = None
    travel_date: Optional[str] = None
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    departure_date: Optional[str] = None
    max_weight: Optional[float] = 20.0


@router.post("/create")
def create_trip(
    body: Optional[CreateTripRequest] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    travel_date: Optional[str] = None,
    origin_city: Optional[str] = None,
    destination_city: Optional[str] = None,
    departure_date: Optional[str] = None,
    max_weight: Optional[float] = 20.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ["traveler", "admin"]:
        raise HTTPException(
            status_code=403,
            detail=f"Only travelers can create trips (your role is '{user.role}')",
        )

    trip_origin = (
        (body.origin if body and body.origin else None)
        or (body.origin_city if body and body.origin_city else None)
        or origin
        or origin_city
    )
    trip_dest = (
        (body.destination if body and body.destination else None)
        or (body.destination_city if body and body.destination_city else None)
        or destination
        or destination_city
    )
    trip_date_str = (
        (body.travel_date if body and body.travel_date else None)
        or (body.departure_date if body and body.departure_date else None)
        or travel_date
        or departure_date
    )
    trip_weight = (
        (body.max_weight if body and body.max_weight is not None else None)
        or (max_weight if max_weight is not None else 20.0)
    )

    if not trip_origin or not trip_dest or not trip_date_str:
        raise HTTPException(
            status_code=400,
            detail="origin, destination, and departure_date are required",
        )

    parsed_date = None
    cleaned_date = trip_date_str.strip().replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y, %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            parsed_date = datetime.strptime(cleaned_date, fmt)
            break
        except Exception:
            pass

    if not parsed_date:
        try:
            parsed_date = datetime.fromisoformat(cleaned_date)
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
