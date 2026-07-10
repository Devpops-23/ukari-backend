from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user

router = APIRouter()


@router.get("/webhook-test")
def webhook_test():
    return {"status": "webhook router is working"}
    # ⭐ Payout created (Stripe has initiated the payout)
    if event_type == "payout.created":
        payout = event["data"]["object"]
        print("Payout created:", payout["id"], payout["amount"])

    # ⭐ Payout paid (money has reached the bank)
    if event_type == "payout.paid":
        payout = event["data"]["object"]
        print("Payout PAID:", payout["id"], payout["amount"])

    # ⭐ Payout failed (bank rejected it)
    if event_type == "payout.failed":
        payout = event["data"]["object"]
        print("Payout FAILED:", payout["id"], payout["failure_message"])

    # ⭐ Payout canceled (Stripe or bank canceled it)
    if event_type == "payout.canceled":
        payout = event["data"]["object"]
        print("Payout CANCELED:", payout["id"])
