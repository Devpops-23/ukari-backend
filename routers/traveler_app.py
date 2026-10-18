from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from db_utils.db import get_db
from db_utils.models import User, Trip, Order, OrderEvent
from utils.auth import get_current_user
from schemas import TravelerOut, TripOut, OrderOut

router = APIRouter(tags=["Traveler"])


def format_traveler_delivery(order: Order):
    earned = order.amount_earned or (order.traveler_fee_cents / 100.0 if order.traveler_fee_cents else order.traveler_fee or 0.0)
    return {
        "id": order.id,
        "order_id": order.id,
        "item_name": order.item_name,
        "delivery_location": order.delivery_location,
        "pickup_location": order.pickup_location,
        "status": order.status,
        "amount_earned": earned,
        "traveler_fee": earned,
        "delivery_deadline": order.delivery_deadline.isoformat() if order.delivery_deadline else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "dispute_id": order.id if order.status == "disputed" or order.dispute_status else None,
        "dispute_reason": order.dispute_reason,
        "proof_photo_url": order.proof_photo_url,
    }


# ---------------------------------------------------------
# CURRENT TRAVELER PROFILE
# ---------------------------------------------------------
@router.get("/traveler/current", response_model=TravelerOut)
def get_my_profile(traveler: User = Depends(get_current_user)):
    return traveler


# ---------------------------------------------------------
# TRAVELER DASHBOARD SUMMARY
# ---------------------------------------------------------
@router.get("/traveler/dashboard")
def get_traveler_dashboard(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_trips = db.query(Trip).filter(
        Trip.traveler_id == traveler.id,
        Trip.status == "active"
    ).count()

    delivered_orders = db.query(Order).filter(
        Order.traveler_id == traveler.id,
        Order.status.in_(["delivered", "buyer_confirmed", "paid"])
    ).count()

    orders = db.query(Order).filter(
        Order.traveler_id == traveler.id,
        Order.status.in_(["delivered", "buyer_confirmed", "paid"])
    ).all()

    total_earned = sum(
        o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee or 0.0)
        for o in orders
    )

    return {
        "status": "success",
        "name": traveler.full_name or "Traveler",
        "traveler_id": traveler.id,
        "active_trips": active_trips,
        "delivered_orders": delivered_orders,
        "total_earned": round(total_earned, 2),
    }


# ---------------------------------------------------------
# GET ALL TRIPS FOR CURRENT TRAVELER
# ---------------------------------------------------------
@router.get("/traveler/trips", response_model=list[TripOut])
def get_my_trips(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trips = (
        db.query(Trip)
        .filter(Trip.traveler_id == traveler.id)
        .order_by(Trip.id.desc())
        .all()
    )
    return trips


# ---------------------------------------------------------
# GET A SPECIFIC TRIP
# ---------------------------------------------------------
@router.get("/traveler/trips/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: int,
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.traveler_id == traveler.id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return trip


# ---------------------------------------------------------
# GET ALL ORDERS FOR CURRENT TRAVELER
# ---------------------------------------------------------
@router.get("/traveler/orders")
@router.get("/orders/traveler")
def get_my_orders(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.traveler_id == traveler.id)
        .order_by(Order.id.desc())
        .all()
    )
    return {"status": "success", "orders": [format_traveler_delivery(o) for o in orders]}


# ---------------------------------------------------------
# GET A SPECIFIC ORDER
# ---------------------------------------------------------
@router.get("/traveler/orders/{order_id}")
def get_order(
    order_id: int,
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.traveler_id == traveler.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return format_traveler_delivery(order)


# ---------------------------------------------------------
# TRAVELER DELIVERIES
# ---------------------------------------------------------
@router.get("/traveler/deliveries")
def get_traveler_deliveries(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deliveries = (
        db.query(Order)
        .filter(Order.traveler_id == traveler.id)
        .order_by(Order.id.desc())
        .all()
    )
    return {
        "status": "success",
        "deliveries": [format_traveler_delivery(d) for d in deliveries],
    }


# ---------------------------------------------------------
# UPLOAD DELIVERY PROOF
# ---------------------------------------------------------
@router.post("/traveler/deliveries/{order_id}/proof")
def upload_delivery_proof(
    order_id: int,
    proof: Optional[UploadFile] = File(None),
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.traveler_id == traveler.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    filename = proof.filename if proof else "proof_uploaded.jpg"
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()
    order.proof_photo_url = f"/proofs/{order_id}_{filename}"

    event = OrderEvent(
        order_id=order.id,
        event_type="delivery_confirmed",
        description=f"Traveler uploaded delivery proof: {filename}",
        message="Delivery completed with proof.",
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Delivery proof uploaded", "order": format_traveler_delivery(order)}


# ---------------------------------------------------------
# TRAVELER DISPUTES
# ---------------------------------------------------------
@router.get("/traveler/disputes")
def get_traveler_disputes(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    disputed_orders = (
        db.query(Order)
        .filter(
            Order.traveler_id == traveler.id,
            Order.status.in_(["disputed", "under_review", "refunded"])
        )
        .order_by(Order.id.desc())
        .all()
    )

    disputes = [
        {
            "id": o.id,
            "dispute_id": o.id,
            "order_id": o.id,
            "item_name": o.item_name,
            "dispute_reason": o.dispute_reason or "Customer reported issue",
            "status": o.dispute_status or "pending",
            "created_at": o.dispute_created_at.isoformat() if o.dispute_created_at else None,
        }
        for o in disputed_orders
    ]

    return {"status": "success", "disputes": disputes}


# ---------------------------------------------------------
# TRAVELER DISPUTE RESPONSE
# ---------------------------------------------------------
@router.post("/traveler/disputes/{order_id}/response")
def respond_to_dispute(
    order_id: int,
    response_text: Optional[str] = Form(None),
    evidence: Optional[UploadFile] = File(None),
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.traveler_id == traveler.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.dispute_status = "under_review"

    event = OrderEvent(
        order_id=order.id,
        event_type="dispute_response",
        description=f"Traveler submitted dispute rebuttal: {response_text or 'Evidence attached'}",
        message=response_text or "Evidence submitted",
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Response submitted"}


# ---------------------------------------------------------
# TRAVELER EARNINGS PER TRIP
# ---------------------------------------------------------
@router.get("/traveler/earnings/trips")
def get_traveler_trip_earnings(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trips = (
        db.query(Trip)
        .filter(Trip.traveler_id == traveler.id)
        .order_by(Trip.id.desc())
        .all()
    )

    trips_data = []
    total = 0.0
    completed = 0.0
    pending = 0.0

    for t in trips:
        trip_orders = db.query(Order).filter(Order.trip_id == t.id).all()
        orders_data = []
        trip_earned = 0.0

        for o in trip_orders:
            earned = o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee or 0.0)
            orders_data.append({
                "id": o.id,
                "order_id": o.id,
                "item_name": o.item_name,
                "amount": earned,
                "status": o.status,
            })
            trip_earned += earned
            if o.status in ["delivered", "buyer_confirmed", "paid"]:
                completed += earned
            else:
                pending += earned

        trips_data.append({
            "id": t.id,
            "trip_id": t.id,
            "origin": t.origin,
            "destination": t.destination,
            "date": (t.travel_date or t.departure_date or t.created_at).isoformat() if (t.travel_date or t.departure_date or t.created_at) else None,
            "total_earned": round(trip_earned, 2),
            "orders": orders_data,
        })
        total += trip_earned

    return {
        "status": "success",
        "total": round(total, 2),
        "completed": round(completed, 2),
        "pending": round(pending, 2),
        "trips": trips_data,
    }


# ---------------------------------------------------------
# TRAVELER ONBOARDING STATUS & COMPLETION
# ---------------------------------------------------------
@router.get("/traveler/onboarding")
def get_onboarding_status(
    traveler: User = Depends(get_current_user),
):
    has_stripe = bool(traveler.stripe_account_id)
    return {
        "status": "success",
        "stripe_status": "active" if has_stripe else "pending",
        "needs_stripe_onboarding": not has_stripe,
        "onboarded": traveler.status == "active",
    }


@router.post("/traveler/onboarding/complete")
def complete_onboarding(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    traveler.status = "active"
    db.commit()
    db.refresh(traveler)
    return {"status": "success", "message": "Onboarding completed"}


# ---------------------------------------------------------
# TRAVELER PAYOUTS HISTORY
# ---------------------------------------------------------
@router.get("/payouts/traveler")
def get_traveler_payouts(
    traveler: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paid_orders = (
        db.query(Order)
        .filter(
            Order.traveler_id == traveler.id,
            Order.status.in_(["delivered", "buyer_confirmed", "paid"])
        )
        .order_by(Order.id.desc())
        .all()
    )

    payouts = [
        {
            "payout_id": o.id,
            "order_id": o.id,
            "amount": o.amount_earned or (o.traveler_fee_cents / 100.0 if o.traveler_fee_cents else o.traveler_fee or 0.0),
            "status": "completed" if o.status in ["buyer_confirmed", "paid"] else "processing",
            "stripe_transfer_id": o.stripe_transfer_id or f"tr_mock_{o.id}",
            "created_at": (o.delivered_at or o.created_at).isoformat() if (o.delivered_at or o.created_at) else None,
        }
        for o in paid_orders
    ]

    return {"status": "success", "payouts": payouts}






