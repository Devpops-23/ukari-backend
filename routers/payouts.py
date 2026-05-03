from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils.db import get_db
from db_utils.models import User, Order, OrderEvent
from auth.auth_router import get_current_traveler  # JWT-based auth


router = APIRouter()


# ---------------------------------------------------------
# Helper: Log order events
# ---------------------------------------------------------
def log_event(db: Session, order_id: int, event_type: str, description: str):
    event = OrderEvent(
        order_id=order_id,
        event_type=event_type,
        message=description,
    )
    db.add(event)
    db.commit()


# ---------------------------------------------------------
# ADMIN: RELEASE TRAVELER PAYOUT AFTER DELIVERY CONFIRMED
# ---------------------------------------------------------
@router.post("/release/{order_id}")
def release_traveler_payout(
    order_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    # Authenticate admin
    user = get_current_traveler(token=token, db=db)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    # Fetch order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Enforce buyer confirmation
    if order.status != "buyer_confirmed":
        raise HTTPException(
            status_code=400,
            detail="Order is not ready for payout (buyer has not confirmed delivery)"
        )

    if not order.traveler_id:
        raise HTTPException(status_code=400, detail="Order has no assigned traveler")

    traveler = db.query(User).filter(User.id == order.traveler_id).first()
    if not traveler:
        raise HTTPException(status_code=404, detail="Traveler not found")

    if not traveler.stripe_account_id:
        raise HTTPException(status_code=400, detail="Traveler has no Stripe connected account")

    if not order.traveler_fee:
        raise HTTPException(status_code=400, detail="Order has no traveler fee set")

    amount_cents = int(round(order.traveler_fee * 100))

    # Stripe Connect transfer
    transfer = create_traveler_payout(
        traveler_stripe_account_id=traveler.stripe_account_id,
        amount_cents=amount_cents,
        order_id=order.id,
    )

    # Mark order as paid
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    # Log event
    log_event(
        db=db,
        order_id=order.id,
        event_type="payout_released",
        description=f"Payout of ${order.traveler_fee} released to traveler {traveler.id}",
    )

    return {
        "status": "success",
        "message": "Traveler payout released and order marked as paid",
        "order_id": order.id,
        "traveler_id": traveler.id,
        "payout": {
            "transfer_id": transfer["id"],
            "amount_cents": transfer["amount"],
            "currency": transfer["currency"],
            "destination": transfer["destination"],
            "status": transfer["status"],
        },
    }
