from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order
from utils.auth import get_current_user

router = APIRouter(tags=["Admin Disputes"])


def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------
# 1. GET ALL DISPUTED ORDERS
# ---------------------------------------------------------
@router.get("/disputes")
def get_disputes(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    disputes = (
        db.query(Order)
        .filter(Order.status == "disputed")
        .order_by(Order.id.desc())
        .all()
    )

    formatted = []
    for d in disputes:
        formatted.append({
            "id": d.id,
            "dispute_id": d.id,
            "order_id": d.id,
            "amount": d.total_charged or (d.total_charged_cents / 100.0 if d.total_charged_cents else d.item_price),
            "buyer_id": d.buyer_id,
            "buyer_name": f"Buyer #{d.buyer_id}",
            "traveler_id": d.traveler_id,
            "traveler_name": f"Traveler #{d.traveler_id}" if d.traveler_id else "Unassigned",
            "reason": d.dispute_reason or "Buyer opened dispute",
            "dispute_reason": d.dispute_reason or "Buyer opened dispute",
            "status": d.dispute_status or "under_review",
            "dispute_status": d.dispute_status or "under_review",
            "created_at": d.dispute_created_at.isoformat() if d.dispute_created_at else (d.created_at.isoformat() if d.created_at else None),
        })

    return {"status": "success", "disputes": formatted}


# ---------------------------------------------------------
# 2. GET SINGLE DISPUTE
# ---------------------------------------------------------
@router.get("/disputes/{dispute_id}")
def get_dispute_detail(
    dispute_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    d = db.query(Order).filter(Order.id == dispute_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")

    return {
        "status": "success",
        "dispute": {
            "id": d.id,
            "dispute_id": d.id,
            "order_id": d.id,
            "amount": d.total_charged or (d.total_charged_cents / 100.0 if d.total_charged_cents else d.item_price),
            "buyer_id": d.buyer_id,
            "buyer_name": f"Buyer #{d.buyer_id}",
            "traveler_id": d.traveler_id,
            "traveler_name": f"Traveler #{d.traveler_id}" if d.traveler_id else "Unassigned",
            "reason": d.dispute_reason or "Buyer opened dispute",
            "dispute_reason": d.dispute_reason or "Buyer opened dispute",
            "status": d.dispute_status or "under_review",
            "dispute_status": d.dispute_status or "under_review",
            "created_at": d.dispute_created_at.isoformat() if d.dispute_created_at else (d.created_at.isoformat() if d.created_at else None),
        },
    }


class DisputeStatusRequest(BaseModel):
    status: str


@router.post("/disputes/{dispute_id}/status")
def update_dispute_status(
    dispute_id: int,
    body: DisputeStatusRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == dispute_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Dispute not found")

    order.dispute_status = body.status
    db.commit()

    return {"status": "success", "dispute_id": order.id, "new_status": body.status}


# ---------------------------------------------------------
# 3. REFUND BUYER FOR DISPUTE
# ---------------------------------------------------------
@router.post("/disputes/{order_id}/refund")
def refund_dispute(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "refunded"
    order.dispute_status = "resolved_refunded"
    order.refunded_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "message": f"Order {order_id} refunded to buyer"}


# ---------------------------------------------------------
# 4. RESOLVE DISPUTE IN FAVOR OF TRAVELER
# ---------------------------------------------------------
@router.post("/disputes/{order_id}/resolve")
def resolve_dispute(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "paid"
    order.dispute_status = "resolved_payout_released"
    db.commit()

    return {"status": "success", "message": f"Dispute on order {order_id} resolved. Payout released to traveler."}
