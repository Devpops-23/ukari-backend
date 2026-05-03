def create_traveler_payout(traveler_stripe_account_id, amount_cents, order_id):
    import stripe
    transfer = stripe.Transfer.create(
        amount=amount_cents,
        currency="usd",
        destination=traveler_stripe_account_id,
        metadata={"order_id": order_id},
    )
    return transfer
