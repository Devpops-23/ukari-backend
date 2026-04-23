# routers/stripe_webhook.py

import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, User
from utils.event_logger import log_event

router = APIRouter(
    prefix="/internal/stripe",
    tags=["Stripe Webhooks"],
)

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    event_type = event["type"]

    # ---------------------------------------------------------
    # HANDLE CHARGEBACKS
    # ---------------------------------------------------------
    if event_type == "charge.dispute.created":
        dispute = event["data"]["object"]
        order_id = dispute["metadata"].get("ukari_order_id")

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                buyer = db.query(User).filter(User.id == order.buyer_id).first()
                if buyer:
                    buyer.chargeback_count += 1
                    db.commit()

                order.status = "disputed"
                db.commit()

                log_event(
                    db=db,
                    order_id=order.id,
                    event_type="chargeback",
                    description="Stripe dispute opened by buyer",
                )

    # ---------------------------------------------------------
    # HANDLE REFUNDS
    # ---------------------------------------------------------
    if event_type == "charge.refunded":
        refund = event["data"]["object"]
        order_id = refund["metadata"].get("ukari_order_id")

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = "refunded"
                db.commit()

                log_event(
                    db=db,
                    order_id=order.id,
                    event_type="refund",
                    description="Stripe refund processed",
                )

    return {"status": "success"}

