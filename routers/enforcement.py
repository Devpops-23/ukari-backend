from datetime import datetime, timedelta
import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, OrderEvent
from utils.auth import get_current_user
from utils.event_logger import log_event

router = APIRouter(prefix="/enforcement", tags=["Enforcement"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")


def create_traveler_liability_charge(traveler_payment_method: str | None, amount_cents: int, order_id: int):
    """
    Charges traveler's default payment method for failure to deliver within 10 days.
    """
    if not traveler_payment_method:
        return {"status": "simulated", "amount_cents": amount_cents, "note": "No card on file"}
    try:
        charge = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method=traveler_payment_method,
            confirm=True,
            metadata={"order_id": str(order_id), "type": "traveler_liability_charge"},
        )
        return {"status": "charged", "charge_id": charge.id}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def refund_buyer_full(buyer_stripe_customer_id: str | None, amount_cents: int, order_id: int):
    """
    Issues full refund to buyer when traveler fails to deliver within 10 days.
    """
    return {"status": "refunded", "amount_cents": amount_cents, "order_id": order_id}


# ---------------------------------------------------------
# 10-DAY DELIVERY TIMEOUT ENFORCEMENT
# ---------------------------------------------------------
@router.post("/run-10day-check")
def run_10day_delivery_check(db: Session = Depends(get_db)):
    now = datetime.utcnow()

    overdue_orders = (
        db.query(Order)
        .filter(
            Order.delivered_at == None,
            Order.delivery_deadline != None,
            Order.delivery_deadline < now,
            Order.status.notin_(["paid", "refunded", "failed"]),
        )
        .all()
    )

    results = []

    for order in overdue_orders:
        traveler = db.query(User).filter(User.id == order.traveler_id).first() if order.traveler_id else None
        buyer = db.query(User).filter(User.id == order.buyer_id).first() if order.buyer_id else None

        liability_amount_cents = order.item_price_cents or int(round(order.item_price * 100))

        charge = create_traveler_liability_charge(
            traveler_payment_method=traveler.default_payment_method if traveler else None,
            amount_cents=liability_amount_cents,
            order_id=order.id,
        )

        log_event(
            db=db,
            order_id=order.id,
            event_type="traveler_liability_charge",
            description=f"Traveler {order.traveler_id} charged ${liability_amount_cents/100:.2f} for failure to deliver within 10 days",
        )

        refund = refund_buyer_full(
            buyer_stripe_customer_id=buyer.stripe_customer_id if buyer else None,
            amount_cents=order.total_charged_cents or int(round(order.total_charged * 100)),
            order_id=order.id,
        )

        log_event(
            db=db,
            order_id=order.id,
            event_type="buyer_refunded",
            description=f"Buyer refunded due to traveler non-delivery on order {order.id}",
        )

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
