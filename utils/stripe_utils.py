import stripe
import os

# Load Stripe secret key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_transfer(amount_cents: int, destination_account: str, description: str = "U-KARI transfer"):
    """
    Create a Stripe transfer from the platform to a connected account.
    """
    return stripe.Transfer.create(
        amount=amount_cents,
        currency="usd",
        destination=destination_account,
        description=description,
    )


def create_payout(amount_cents: int, connected_account: str, description: str = "U-KARI payout"):
    """
    Create a payout from a connected account to the traveler's bank.
    """
    return stripe.Payout.create(
        amount=amount_cents,
        currency="usd",
        description=description,
        stripe_account=connected_account,
    )


def get_balance(connected_account: str = None):
    """
    Get balance for platform or connected account.
    """
    if connected_account:
        return stripe.Balance.retrieve(stripe_account=connected_account)
    return stripe.Balance.retrieve()
