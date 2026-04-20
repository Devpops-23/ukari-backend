# routers/traveler_app.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from db_utils.db import get_db
from db_utils.models import Order, Trip, User, OrderEvent
from routers import traveler
from utils.auth import get_current_user

router = APIRouter(prefix="/traveler", tags=["Traveler App"])


# ---------------------------------------------------------
# 1. Traveler Dashboard Summary
# ---------------------------------------------------------
@router.get("/dashboard")
def traveler_dashboard(token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    active_trips = (
        db.query(Trip)
        .filter(Trip.traveler_id == traveler.id, Trip.status == "active")
        .all()
    )

    assigned_orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler.id, Order.status.in_(["accepted", "in_transit"]))
        .all()
    )

    delivered_orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler.id, Order.status == "buyer_confirmed")
        .all()
    )

    total_earnings = sum([o.traveler_fee for o in delivered_orders if o.traveler_fee])

    return {
        "status": "success",
        "traveler_id": traveler.id,
        "active_trips": len(active_trips),
        "assigned_orders": len(assigned_orders),
        "completed_deliveries": len(delivered_orders),
        "total_earnings": round(total_earnings, 2),
    }


# ---------------------------------------------------------
# 2. Traveler Active Trips (UI List)
# ---------------------------------------------------------
@router.get("/trips")
def traveler_trips(token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    trips = (
        db.query(Trip)
        .filter(Trip.traveler_id == traveler.id)
        .order_by(Trip.created_at.desc())
        .all()
    )

    return {
        "status": "success",
        "trips": [
            {
                "trip_id": t.id,
                "origin": t.origin,
                "destination": t.destination,
                "travel_date": t.travel_date.isoformat(),
                "max_weight": t.max_weight,
                "status": t.status,
            }
            for t in trips
        ],
    }


# ---------------------------------------------------------
# 3. Matching Orders for a Trip (UI List)
# ---------------------------------------------------------
@router.get("/trip/{trip_id}/matches")
def trip_matches(trip_id: int, token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.traveler_id == traveler.id)
        .first()
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    orders = (
        db.query(Order)
        .filter(
            Order.status == "pending",
            Order.delivery_location == trip.destination,
            Order.item_price <= trip.max_weight,
        )
        .order_by(Order.created_at.desc())
        .all()
    )

    return {
        "status": "success",
        "trip_id": trip.id,
        "matches": [
            {
                "order_id": o.id,
                "item_name": o.item_name,
                "weight": o.item_price,
                "traveler_fee": o.traveler_fee,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
    }


# ---------------------------------------------------------
# 4. Traveler Accepts an Order
# ---------------------------------------------------------
@router.post("/order/{order_id}/accept")
def accept_order(order_id: int, token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not available")

    order.traveler_id = traveler.id
    order.status = "accepted"
    order.accepted_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Order accepted",
        "order_id": order.id,
    }

# Enforce 2-week rule
trip = (
    db.query(Trip)
    .filter(Trip.traveler_id == traveler.id, Trip.status == "active")
    .first()
)

if trip:
    expected_arrival = datetime.utcnow() + timedelta(days=5)
    if trip.travel_date < expected_arrival + timedelta(days=14):
        raise HTTPException(
            status_code=400,
            detail="You cannot accept this order because the package will not arrive at least 2 weeks before your departure date."
        )

# ---------------------------------------------------------
# 5. Traveler Marks Order as Delivered
# ---------------------------------------------------------
@router.post("/order/{order_id}/delivered")
def mark_delivered(order_id: int, token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    order = db.query(Order).filter(Order.id == order_id, Order.traveler_id == traveler.id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.status not in ["accepted", "in_transit"]:
        raise HTTPException(status_code=400, detail="Order cannot be marked delivered")

    order.status = "delivered"
    order.delivered_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Order marked as delivered. Waiting for buyer confirmation.",
        "order_id": order.id,
    }


# ---------------------------------------------------------
# 6. Traveler Notifications Feed
# ---------------------------------------------------------
@router.get("/notifications")
def traveler_notifications(token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    events = (
        db.query(OrderEvent)
        .join(Order, OrderEvent.order_id == Order.id)
        .filter(Order.traveler_id == traveler.id)
        .order_by(OrderEvent.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "status": "success",
        "notifications": [
            {
                "order_id": e.order_id,
                "type": e.event_type,
                "description": e.description,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
    buyer = db.query(User).filter(User.id == order.buyer_id).first()

    notify_user(
        db=db,
        user=buyer,
        order_id=order.id,
        title="Traveler Accepted",
        message="A traveler has accepted your order and will deliver it soon.",
        event_type="order_accepted",
)
    buyer = db.query(User).filter(User.id == order.buyer_id).first()

    notify_user(
    db=db,
    user=buyer,
    order_id=order.id,
    title="Package Delivered",
    message="Your package has been delivered. Please confirm delivery.",
    event_type="delivery_marked",
)
