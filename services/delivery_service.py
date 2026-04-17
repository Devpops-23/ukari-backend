import stripe
from datetime import datetime
from db_utils.db import (
    get_overdue_deliveries,
    mark_delivery_failed,
    mark_auto_charge_executed,
)


def process_overdue_deliveries():
    now = datetime.utcnow()
    overdue = get_overdue_deliveries(now)

    for delivery in overdue:
        try:
            # 1. Charge the traveler (penalty)
            charge = stripe.PaymentIntent.create(
                amount=delivery.item_price_cents,
                currency="usd",
                customer=delivery.traveler_stripe_customer_id,
                payment_method=delivery.traveler_payment_method_id,
                confirm=True,
                off_session=True,
                description=f"Penalty charge for failed delivery #{delivery.id}",
            )

            print(f"Traveler charged for failed delivery {delivery.id}")

            # 2. Refund the buyer
            refund = stripe.Refund.create(
                payment_intent=delivery.buyer_payment_intent_id,
                amount=delivery.item_price_cents
            )

            print(f"Buyer refunded for delivery {delivery.id}")

        except stripe.error.CardError as e:
            # Traveler's card failed (insufficient funds, expired, etc.)
            print(f"Traveler card failed for delivery {delivery.id}: {str(e)}")
            continue

        # 3. Mark delivery as failed
        mark_delivery_failed(delivery.id)

        # 4. Prevent double-charging
        mark_auto_charge_executed(delivery.id)

        print(f"Completed penalty cycle for delivery {delivery.id}")

