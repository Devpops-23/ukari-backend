from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, OrderEvent
from utils.auth import get_current_user

router = APIRouter(
    prefix="/admin/timeline",
    tags=["Admin Timeline"]
)

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
@router.get("/order/{order_id}")
def get_order_timeline(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
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
    admin = get_current_user(db, token)
    if admin.role != "admin":
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
    admin = get_current_user(db, token)
    if admin.role != "admin":
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

