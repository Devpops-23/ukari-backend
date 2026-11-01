
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Trip, Order
from utils.auth import get_current_user

router = APIRouter(tags=["Traveler"])


# ---------------------------------------------------------
# BUYER SEARCHES AVAILABLE TRAVELERS BEFORE SHOPPING
# ---------------------------------------------------------

@router.get("/travelers/available")
def find_available_travelers(
    destination: str = Query(
        ...,
        min_length=2,
        description="Destination city or country, for example Accra or Ghana",
    ),
    buyer: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return active traveler trips matching the buyer's destination.

    Only the traveler's first name is exposed.
    The buyer receives traveler_id and trip_id for checkout.
    """

    if getattr(buyer, "role", None) != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can search for available travelers.",
        )

    matching_trips = (
        db.query(Trip, User)
        .join(User, Trip.traveler_id == User.id)
        .filter(
            Trip.status == "active",
            Trip.destination.ilike(f"%{destination.strip()}%"),
            User.role == "traveler",
            User.status == "active",
        )
        .order_by(
            Trip.departure_date.asc(),
            Trip.id.desc(),
        )
        .all()
    )

    results = []

    for trip, traveler in matching_trips:

        # Expose first name only
        full_name = (getattr(traveler, "full_name", "") or "").strip()

        first_name = (
            full_name.split()[0]
            if full_name
            else "Traveler"
        )

        trip_date = (
            getattr(trip, "travel_date", None)
            or getattr(trip, "departure_date", None)
            or getattr(trip, "created_at", None)
        )

        results.append({
            "traveler_id": traveler.id,
            "trip_id": trip.id,
            "first_name": first_name,
            "origin": trip.origin,
            "destination": trip.destination,
            "departure_date": (
                trip_date.isoformat()
                if trip_date else None
            ),
            "trip_status": trip.status,
        })

    return {
        "status": "success",
        "destination_searched": destination.strip(),
        "count": len(results),
        "travelers": results,
        "next_step": (
            "Select a traveler and use traveler_id "
            "and trip_id at shopping checkout."
        ),
    }


# ---------------------------------------------------------
# FORMAT TRAVELER DELIVERY INFORMATION
# ---------------------------------------------------------

def format_traveler_delivery(order: Order):
    """
    Format order information for the traveler dashboard.
    """

    amount_earned = getattr(order, "amount_earned", None)

    if amount_earned is None:
        traveler_fee_cents = getattr(
            order, "traveler_fee_cents", None
        )

        if traveler_fee_cents is not None:
            amount_earned = traveler_fee_cents / 100.0
        else:
            amount_earned = (
                getattr(order, "traveler_fee", None) or 0.0
            )

    disputed = (
        getattr(order, "status", None) == "disputed"
        or bool(getattr(order, "dispute_status", None))
    )

    return {
        "id": order.id,
        "order_id": order.id,
        "item_name": getattr(order, "item_name", None),
        "delivery_location": getattr(
            order, "delivery_location", None
        ),
        "pickup_location": getattr(
            order, "pickup_location", None
        ),
        "status": getattr(order, "status", None),
        "amount_earned": amount_earned,
        "traveler_fee": amount_earned,

        "delivery_deadline": (
            order.delivery_deadline.isoformat()
            if getattr(order, "delivery_deadline", None)
            else None
        ),

        "delivered_at": (
            order.delivered_at.isoformat()
            if getattr(order, "delivered_at", None)
            else None
        ),

        "created_at": (
            order.created_at.isoformat()
            if getattr(order, "created_at", None)
            else None
        ),

        "dispute_id": order.id if disputed else None,

        "dispute_reason": getattr(
            order, "dispute_reason", None
        ),
    }
