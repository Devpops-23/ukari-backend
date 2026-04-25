import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
DATABASE_URL = os.getenv("DATABASE_URL")

# JWT
SECRET = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

# Stripe
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
print("DEBUG STRIPE KEY:", STRIPE_API_KEY)

if not STRIPE_API_KEY:
    raise RuntimeError("STRIPE_API_KEY is not set")





