import stripe
import os
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from db_utils.db import get_db
from db_utils.models import Order
from datetime import datetime

router = APIRouter(prefix="/webhook", tags=["Stripe Webhook"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # set this in Render

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = get_db()):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    # -----------------------------
    # PAYOUT CREATED
    # -----------------------------
    if event["type"] == "payout.created":
        payout = event["data"]["object"]
        order_id = payout["metadata"].get("order_id")

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.payout_status = "created"
                db.commit()

    # -----------------------------
    # PAYOUT PAID (SUCCESS)
    # -----------------------------
    if event["type"] == "payout.paid":
        payout = event["data"]["object"]
        order_id = payout["metadata"].get("order_id")

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.payout_status = "paid"
                order.payout_paid_at = datetime.utcnow()
                db.commit()

    # -----------------------------
    # PAYOUT FAILED
    # -----------------------------
    if event["type"] == "payout.failed":
        payout = event["data"]["object"]
        order_id = payout["metadata"].get("order_id")

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.payout_status = "failed"
                db.commit()

    return {"status": "success"}



