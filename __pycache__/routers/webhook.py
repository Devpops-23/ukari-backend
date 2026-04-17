from fastapi import APIRouter, Request, HTTPException
import os
import stripe

router = APIRouter()

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle events
    if event["type"] == "payout.paid":
        payout = event["data"]["object"]
        print("Payout succeeded:", payout["id"])

    elif event["type"] == "payout.failed":
        payout = event["data"]["object"]
        print("Payout failed:", payout["id"])

    return {"status": "success"}
