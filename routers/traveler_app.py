from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Traveler, Order, Trip
from schemas import TravelerOut, TripOut, OrderOut
from auth import get_current_traveler

router = APIRouter(
    prefix="/traveler",
    tags=["Traveler App"]
)

# ---------------------------------------------------------
# GET TRAVELER DASHBOARD SUMMARY
# ---------------------------------------------------------
@router.get("/dashboard")
def traveler_dashboard(
    traveler: Traveler = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    active_trips = db.query(Trip).filter(
        Trip.traveler_id == traveler.id,
        Trip.status == "active"
    ).count()

    delivered_orders = db.query(Order).filter(
        Order.traveler_id == traveler.id,
        Order.status == "delivered"
    ).count()

    total_earned = db.query(Order).filter(
        Order.traveler_id == traveler.id,
        Order.status == "delivered"
    ).with_entities(
        Order.amount_earned
    ).all()

    total_earned = sum(o[0] or 0 for o in total_earned)

    return {
        "traveler_id": traveler.id,
        "name": traveler.name,
        "active_trips": active_trips,
        "delivered_orders": delivered_orders,
        "total_earned": total_earned
    }


# ---------------------------------------------------------
# GET TRAVELER EARNINGS + DELIVERED ORDERS
# ---------------------------------------------------------
@router.get("/earnings")
def traveler_earnings(
    traveler: Traveler = Depends(get_current_traveler),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(
        Order.traveler_id == traveler.id,
        Order.status == "delivered"
    ).all()

    total = sum(o.amount_earned or 0 for o in orders)

    # Serialize orders safely
    serialized_orders = [
        {
            "id": o.id,
            "package_id": o.package_id,
            "status": o.status,
            "amount_earned": o.amount_earned,
            "delivered_at": o.delivered_at,
        }
        for o in orders
    ]

    return {
        "total_earned": total,
        "orders": serialized_orders
    }    



