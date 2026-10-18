import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Database
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./ukari.db"

# JWT
SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "dev_fallback_secret_key_123456789"
ALGORITHM = "HS256"

# Stripe
STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
print("DEBUG STRIPE KEY:", STRIPE_API_KEY)

if not STRIPE_API_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY or STRIPE_API_KEY is not set")







