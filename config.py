import os
import stripe
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Stripe API Key
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
if not STRIPE_API_KEY:
    raise RuntimeError("STRIPE_API_KEY is not set")

stripe.api_key = STRIPE_API_KEY

