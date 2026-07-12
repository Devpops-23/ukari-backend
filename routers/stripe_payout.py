import stripe
import os
from fastapi import HTTPException

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_traveler_payout(traveler_stripe_account_id: str, amount_cents: int, order_id: int):
    try:
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="usd",
            destination=traveler_stripe_account_id,
            metadata={"order_id": order_id}
        )
        return transfer
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))









