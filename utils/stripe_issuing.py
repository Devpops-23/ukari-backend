# utils/stripe_issuing.py

from typing import Optional, Dict, Any
import os

import stripe


# Initialize Stripe
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
stripe.api_key = STRIPE_API_KEY


# Map marketplace → dedicated virtual card metadata tag
MARKETPLACE_CARD_TAGS = {
    "amazon": "ukari_amazon_card",
    "walmart": "ukari_walmart_card",
    "costco": "ukari_costco_card",
    "macys": "ukari_macys_card",
}


def _get_or_create_virtual_card_for_marketplace(source: str) -> stripe.issuing.Card:
    """
    Get or create a dedicated virtual card for a given marketplace.
    Cards are tagged via metadata so we can reuse them.
    """
    tag = MARKETPLACE_CARD_TAGS.get(source)
    if not tag:
        raise ValueError(f"Unsupported marketplace source: {source}")

    # 1) Try to find existing card
    cards = stripe.issuing.Card.list(
        limit=100,
        expand=["data"],
    )

    for c in cards.auto_paging_iter():
        if c.metadata.get("ukari_marketplace_tag") == tag:
            return c

    # 2) Create new card if none exists
    cardholder_list = stripe.issuing.Cardholder.list(limit=1)
    if not cardholder_list.data:
        # Minimal cardholder for U-KARI as business
        cardholder = stripe.issuing.Cardholder.create(
            type="company",
            name="U-KARI Platform",
            email="admin@ukari.app",
            billing={
                "address": {
                    "line1": "123 Example St",
                    "city": "Houston",
                    "state": "TX",
                    "postal_code": "77001",
                    "country": "US",
                }
            },
        )
    else:
        cardholder = cardholder_list.data[0]

    card = stripe.issuing.Card.create(
        cardholder=cardholder.id,
        currency="usd",
        type="virtual",
        metadata={
            "ukari_marketplace_tag": tag,
            "ukari_marketplace_source": source,
        },
        spending_controls={
            "allowed_categories": ["merchandise", "online_services"],
        },
    )

    return card


def ensure_sufficient_balance(amount_cents: int) -> None:
    """
    Ensure Stripe balance is sufficient to cover a purchase.
    For now, this just checks and raises if not enough.
    Later, you can wire this to external funding.
    """
    balance = stripe.Balance.retrieve()
    available = 0
    for b in balance["available"]:
        if b["currency"] == "usd":
            available += b["amount"]

    if available < amount_cents:
        raise ValueError("Insufficient Stripe balance to fund purchase")


def create_issuing_authorization(
    source: str,
    amount_cents: int,
    merchant_name: str,
    order_id: int,
) -> Dict[str, Any]:
    """
    Simulate / prepare an Issuing authorization for a marketplace purchase.
    In a real integration, Stripe will call your webhook on authorization.
    Here, we just ensure balance and return card info for client-side use.
    """
    ensure_sufficient_balance(amount_cents)

    card = _get_or_create_virtual_card_for_marketplace(source)

    # In a real flow, the actual authorization happens when the card is used
    # at the merchant checkout. Here we just return card details needed
    # for the purchase (you would never expose full PAN in production).
    return {
        "card_id": card.id,
        "last4": card.last4,
        "brand": card.brand,
        "currency": card.currency,
        "amount_cents": amount_cents,
        "merchant_name": merchant_name,
        "order_id": order_id,
    }


def record_issuing_transaction(
    order_id: int,
    source: str,
    amount_cents: int,
    merchant_name: str,
) -> Dict[str, Any]:
    """
    Placeholder to record a completed Issuing transaction.
    In production, this is driven by Stripe webhooks (issuing_authorization.*
    and issuing_transaction.* events).
    """
    # TODO: Persist this in DB (e.g., IssuingTransaction table)
    return {
        "order_id": order_id,
        "source": source,
        "amount_cents": amount_cents,
        "merchant_name": merchant_name,
        "status": "recorded",
    }
