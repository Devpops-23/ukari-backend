# routers/admin_dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, OrderEvent, User
from utils.auth import get_current_user

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


# ---------------------------------------------------------
# FORMATTER: Convert OrderEvent rows → UI-friendly JSON
# ---------------------------------------------------------
def format_event(event: OrderEvent):
    return {
        "type": event.event_type,
        "description": event.description,
        "timestamp": event.created_at.isoformat(),
    }


# ---------------------------------------------------------
# ADMIN: FULL ORDER TIMELINE (UI-READY)
# ---------------------------------------------------------
@router.get("/timeline/{order_id}")
def get_order_timeline(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    traveler = db.query(User).filter(User.id == order.traveler_id).first()

    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.created_at.asc())
        .all()
    )

    # Group events by logical phases
    timeline = {
        "order_created": [],
        "purchase_phase": [],
        "shipment_phase": [],
        "delivery_phase": [],
        "payout_phase": [],
        "enforcement_phase": [],
    }

    for e in events:
        if e.event_type in ["order_created"]:
            timeline["order_created"].append(format_event(e))

        elif e.event_type in ["purchase_started", "purchase_completed"]:
            timeline["purchase_phase"].append(format_event(e))

        elif e.event_type in ["shipment_in_transit", "traveler_received"]:
            timeline["shipment_phase"].append(format_event(e))

        elif e.event_type in ["delivery_confirmed"]:
            timeline["delivery_phase"].append(format_event(e))

        elif e.event_type in ["payout_released"]:
            timeline["payout_phase"].append(format_event(e))

        elif e.event_type in ["traveler_liability_charge", "buyer_refunded", "auto_refunded"]:
            timeline["enforcement_phase"].append(format_event(e))

    return {
        "status": "success",
        "order_id": order.id,
        "buyer": {
            "id": buyer.id,
            "email": buyer.email,
        } if buyer else None,
        "traveler": {
            "id": traveler.id,
            "email": traveler.email,
        } if traveler else None,
        "current_status": order.status,
        "timeline": timeline,
    }


# ---------------------------------------------------------
# ADMIN: ENFORCEMENT LOGS (UI-READY)
# ---------------------------------------------------------
@router.get("/enforcement-logs")
def get_enforcement_logs(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.event_type.in_([
            "traveler_liability_charge",
            "buyer_refunded",
            "auto_refunded",
        ]))
        .order_by(OrderEvent.created_at.desc())
        .all()
    )

    logs = [
        {
            "order_id": e.order_id,
            "type": e.event_type,
            "description": e.description,
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]

    return {
        "status": "success",
        "count": len(logs),
        "logs": logs,
    }


# ---------------------------------------------------------
# ADMIN: FINANCIAL LOGS (Purchases + Payouts)
# ---------------------------------------------------------
@router.get("/financial-logs")
def get_financial_logs(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.event_type.in_([
            "purchase_started",
            "purchase_completed",
            "payout_released",
        ]))
        .order_by(OrderEvent.created_at.desc())
        .all()
    )

    logs = [
        {
            "order_id": e.order_id,
            "type": e.event_type,
            "description": e.description,
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]

    return {
        "status": "success",
        "count": len(logs),
        "logs": logs,
    }

# routers/admin_dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, User, Trip
from utils.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ---------------------------------------------------------
# 1. View all orders
# ---------------------------------------------------------
@router.get("/orders")
def get_all_orders(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    orders = db.query(Order).order_by(Order.id.desc()).all()

    return {
        "status": "success",
        "orders": [
            {
                "order_id": o.id,
                "buyer_id": o.buyer_id,
                "traveler_id": o.traveler_id,
                "status": o.status,
                "price": o.item_price,
                "delivery_location": o.delivery_location,
            }
            for o in orders
        ],
    }


# ---------------------------------------------------------
# 2. View all travelers
# ---------------------------------------------------------
@router.get("/travelers")
def get_travelers(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    travelers = db.query(User).filter(User.role == "traveler").all()

    return {
        "status": "success",
        "travelers": [
            {
                "id": t.id,
                "name": t.name,
                "rating": t.rating,
                "reliability_score": t.reliability_score,
                "on_time": t.on_time_deliveries,
                "late": t.late_deliveries,
                "cancellations": t.cancellation_count,
                "flight_cancels": t.flight_cancel_count,
                "status": t.status,
            }
            for t in travelers
        ],
    }


# ---------------------------------------------------------
# 3. View all buyers
# ---------------------------------------------------------
@router.get("/buyers")
def get_buyers(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    buyers = db.query(User).filter(User.role == "buyer").all()

    return {
        "status": "success",
        "buyers": [
            {
                "id": b.id,
                "name": b.name,
                "chargebacks": b.chargeback_count,
                "returns": b.return_count,
                "status": b.status,
            }
            for b in buyers
        ],
    }


# ---------------------------------------------------------
# 4. View banned users
# ---------------------------------------------------------
@router.get("/banned")
def get_banned_users(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    banned = db.query(User).filter(User.status == "banned").all()

    return {
        "status": "success",
        "banned_users": [
            {
                "id": u.id,
                "name": u.name,
                "role": u.role,
                "chargebacks": u.chargeback_count,
                "returns": u.return_count,
            }
            for u in banned
        ],
    }


# ---------------------------------------------------------
# 5. Trigger reroute
# ---------------------------------------------------------
@router.post("/reroute/{order_id}")
def admin_reroute(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.traveler_id = None
    order.status = "rerouted"
    db.commit()

    return {"status": "success", "message": "Order rerouted"}


# ---------------------------------------------------------
# 6. Trigger repurchase
# ---------------------------------------------------------
@router.post("/repurchase/{order_id}")
def admin_repurchase(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "reordered"
    db.commit()

    return {"status": "success", "message": "Order repurchased"}


# ---------------------------------------------------------
# 7. Trigger auto-assign
# ---------------------------------------------------------
@router.post("/auto-assign/{order_id}")
def admin_auto_assign(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    from utils.matching_engine import find_best_traveler

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    trip = find_best_traveler(db, order)
    if not trip:
        return {"status": "pending", "message": "No eligible travelers available"}

    order.traveler_id = trip.traveler_id
    order.status = "accepted"
    db.commit()

    return {
        "status": "success",
        "message": "Traveler assigned",
        "traveler_id": trip.traveler_id,
    }
