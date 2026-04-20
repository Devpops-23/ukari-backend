# routers/admin_dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, OrderEvent
from utils.auth import get_current_user

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


# ---------------------------------------------------------
# ADMIN: FULL ORDER TIMELINE
# ---------------------------------------------------------
@router.get("/timeline/{order_id}")
def get_order_timeline(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.created_at.asc())
        .all()
    )

    timeline = [
        {
            "event_type": e.event_type,
            "description": e.description,
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]

    return {
        "status": "success",
        "order_id": order_id,
        "timeline": timeline,
    }


# ---------------------------------------------------------
# ADMIN: VIEW ALL ENFORCEMENT ACTIONS
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
            "event_type": e.event_type,
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
