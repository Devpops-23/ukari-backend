import sys
print("RUNNING PYTHON:", sys.executable)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
from db_utils.db import engine
import db_utils.models  # <-- IMPORTANT: ensures models are registered
from db_utils.models import Base

# Create all tables
Base.metadata.create_all(bind=engine)

# -----------------------------
# APP INITIALIZATION
# -----------------------------
app = FastAPI()

# -----------------------------
# CORS CONFIG
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ukari-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ROUTERS
# -----------------------------
from auth.auth_router import router as auth_router

from routers import stripe_connect
from routers import payouts_internal
from routers import stripe_webhook
from routers import orders
from routers import trips
from routers import earnings
from routers import earnings_summary
from routers import trip_earnings
from routers import stripe_balance
from routers import stripe_payout
from routers import stripe_payout_history
from routers.admin_dashboard import router as admin_router
from routers.traveler_app import router as traveler_app_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])

app.include_router(stripe_connect.router)
app.include_router(payouts_internal.router)
app.include_router(stripe_webhook.router)

app.include_router(orders.router)
app.include_router(trips.router)

app.include_router(earnings.router)
app.include_router(earnings_summary.router)
app.include_router(trip_earnings.router)

app.include_router(stripe_balance.router)
app.include_router(stripe_payout.router)
app.include_router(stripe_payout_history.router)
app.include_router(admin_router)
app.include_router(traveler_app_router)

# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def root():
    return {"message": "U-KARI backend running"}


