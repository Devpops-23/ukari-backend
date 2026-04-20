# routers/enforcement.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from db_utils.db import get_db
from db_utils.models import Order, User
from utils.stripe_connect import create_traveler_liability_charge, refund_buyer_full
from utils.event_logger import log_event

router = APIRouter(prefix="/enforcement", tags=["Enforcement"])


# ---------------------------------------------------------
# 10-DAY DELIVERY TIMEOUT ENFORCEMENT
# This endpoint should be called by a CRON job every hour.
# ---------------------------------------------------------
@router.post("/run-10day-check")
def run_10day_delivery_check(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    deadline = now - timedelta(days=10)

    overdue_orders = (
    db.query(Order)
    .filter(
        Order.traveler_arrived_at != None,
        Order.delivery_deadline != None,
        Order.delivered_at == None,
        Order.delivery_deadline < now,
        Order.status.notin_(["paid", "refunded", "failed"]),
    )
    .all()
)


    results = []

    for order in overdue_orders:
        traveler = db.query(User).filter(User.id == order.traveler_id).first()
        buyer = db.query(User).filter(User.id == order.buyer_id).first()

        # -----------------------------
        # 1. Charge traveler full item cost
        # -----------------------------
        liability_amount_cents = int(round(order.item_price * 100))

        charge = create_traveler_liability_charge(
            traveler_payment_method=traveler.default_payment_method,
            amount_cents=liability_amount_cents,
            order_id=order.id,
        )

        log_event(
            db=db,
            order_id=order.id,
            event_type="traveler_liability_charge",
            description=f"Traveler {traveler.id} charged ${order.item_price} for failure to deliver within 10 days",
        )

        # -----------------------------
        # 2. Refund buyer full amount
        # -----------------------------
        refund = refund_buyer_full(
            buyer_stripe_customer_id=buyer.stripe_customer_id,
            amount_cents=int(round(order.total_charged * 100)),
            order_id=order.id,
        )

        log_event(
            db=db,
            order_id=order.id,
            event_type="buyer_refunded",
            description=f"Buyer refunded full amount ${order.total_charged} due to traveler non-delivery",
        )

        # -----------------------------
        # 3. Update order status
        # -----------------------------
        order.status = "failed"
        order.dispute_status = "auto_refunded"
        order.refunded_at = datetime.utcnow()

        db.commit()
        db.refresh(order)

        results.append({
            "order_id": order.id,
            "traveler_charged": charge,
            "buyer_refunded": refund,
            "status": "failed",
        })

    return {
        "status": "success",
        "checked": len(overdue_orders),
        "results": results,
    }

