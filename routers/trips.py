
from datetime import datetime
from math import isfinite
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

    # Alternative field names retained for compatibility
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    departure_date: Optional[str] = None

    # No default: the traveler must declare their own capacity
    max_weight: Optional[float] = None


def parse_trip_date(date_string: str) -> datetime:
    cleaned_date = date_string.strip()

    if not cleaned_date:
        raise HTTPException(
            status_code=400,
            detail="A valid departure date is required.",
        )

    # Support ISO dates with Z timezone notation
    cleaned_date = cleaned_date.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(cleaned_date)
    except ValueError:
        pass

    supported_formats = (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y, %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
    )

    for date_format in supported_formats:
        try:
            return datetime.strptime(cleaned_date, date_format)
        except ValueError:
            continue

    raise HTTPException(
        status_code=400,
        detail="Invalid departure date. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM.",
    )


@router.post("/create")
def create_trip(
    body: Optional[CreateTripRequest] = None,

    # Query parameters retained for compatibility
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    travel_date: Optional[str] = None,
    origin_city: Optional[str] = None,
    destination_city: Optional[str] = None,
    departure_date: Optional[str] = None,
    max_weight: Optional[float] = None,

    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only travelers and admins may create trips
    if user.role not in ["traveler", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only travelers can create trips.",
        )

    # Read values from the JSON body first, then query parameters
    trip_origin = (
        (body.origin if body else None)
        or (body.origin_city if body else None)
        or origin
        or origin_city
    )

    trip_destination = (
        (body.destination if body else None)
        or (body.destination_city if body else None)
        or destination
        or destination_city
    )

    trip_date_string = (
        (body.travel_date if body else None)
        or (body.departure_date if body else None)
        or travel_date
        or departure_date
    )

    trip_weight = (
        body.max_weight
        if body and body.max_weight is not None
        else max_weight
    )

    # Validate required trip information
    if not trip_origin or not trip_destination or not trip_date_string:
        raise HTTPException(
            status_code=400,
            detail="Origin, destination, and departure date are required.",
        )

    # The traveler must personally declare carrying capacity
    if trip_weight is None:
        raise HTTPException(
            status_code=400,
            detail="Please enter your carrying capacity in pounds before creating this trip.",
        )

    if not isfinite(trip_weight) or trip_weight <= 0:
        raise HTTPException(
            status_code=400,
            detail="Carrying capacity must be a positive number of pounds.",
        )

    trip_origin = trip_origin.strip()
    trip_destination = trip_destination.strip()

    if not trip_origin or not trip_destination:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination cannot be empty.",
        )

    parsed_date = parse_trip_date(trip_date_string)

    # Create the trip
    trip = Trip(
        traveler_id=user.id,
        origin=trip_origin,
        destination=trip_destination,
        departure_date=parsed_date,
        travel_date=parsed_date,
        arrival_date=None,
        max_weight=trip_weight,
        status="active",
        total_earned=0.0,
    )

    try:
        db.add(trip)
        db.commit()
        db.refresh(trip)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create trip. Please try again.",
        )

    return {
        "status": "success",
        "message": "Trip created successfully.",
        "trip": {
            "id": trip.id,
            "traveler_id": trip.traveler_id,
            "origin": trip.origin,
            "destination": trip.destination,
            "departure_date": (
                trip.departure_date.isoformat()
                if trip.departure_date
                else None
            ),
            "travel_date": (
                trip.travel_date.isoformat()
                if trip.travel_date
                else None
            ),
            "max_weight": trip.max_weight,
            "status": trip.status,
            "total_earned": trip.total_earned,
        },
    }

