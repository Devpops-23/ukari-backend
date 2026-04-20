# utils/stripe_connect.py

import os
from typing import Dict, Any
import stripe

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
stripe.api_key = STRIPE_API_KEY


def create_traveler_payout(
    traveler_stripe_account_id: str,
    amount_cents: int,
    order_id: int,
) -> Dict[str, Any]:
    """
    Create a Stripe Connect transfer to the traveler.
    This is called ONLY after:
      - Order is delivered
      - Buyer has confirmed delivery
    Stripe's fee is effectively realized at this point in the flow.
    """
    if amount_cents <= 0:
        raise ValueError("Payout amount must be positive")

    transfer = stripe.Transfer.create(
        amount=amount_cents,
        currency="usd",
        destination=traveler_stripe_account_id,
        metadata={
            "ukari_order_id": str(order_id),
            "ukari_role": "traveler_payout",
        },
    )

    return {
        "id": transfer.id,
        "amount": transfer.amount,
        "currency": transfer.currency,
        "destination": transfer.destination,
        "status": transfer.status,
    }
def create_traveler_liability_charge(
    traveler_payment_method: str,
    amount_cents: int,
    order_id: int,
) -> Dict[str, Any]:
    """
    Charge the traveler for the item cost when they fail to deliver within 10 days.
    This is an off-session charge.
    """
    charge = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        payment_method=traveler_payment_method,
        confirm=True,
        off_session=True,
        metadata={
            "ukari_order_id": str(order_id),
            "ukari_role": "traveler_liability_charge",
        },
    )

    return {
        "payment_intent": charge.id,
        "amount": charge.amount,
        "status": charge.status,
    }


def refund_buyer_full(
    buyer_stripe_customer_id: str,
    amount_cents: int,
    order_id: int,
) -> Dict[str, Any]:
    """
    Refund the buyer the full amount they paid.
    Stripe fee = $0 because payout never happened.
    """
    refund = stripe.Refund.create(
        amount=amount_cents,
        metadata={
            "ukari_order_id": str(order_id),
            "ukari_role": "buyer_full_refund",
        },
    )

    return {
        "refund_id": refund.id,
        "amount": refund.amount,
        "status": refund.status,
    }
