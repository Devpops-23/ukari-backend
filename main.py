import os
import stripe
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load Stripe env vars
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

print("PUBLIC:", STRIPE_PUBLIC_KEY)
print("SECRET:", STRIPE_SECRET_KEY)
print("WEBHOOK:", STRIPE_WEBHOOK_SECRET)

stripe.api_key = STRIPE_SECRET_KEY

# FastAPI app
app = FastAPI(
    servers=[{"url": "https://ukari-backend-api.onrender.com"}]
)

# -----------------------------------------
# CORS
# -----------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ukari-frontend-jjak.vercel.app",
        "https://ukari-frontend.vercel.app",
        "https://u-kari.com",
        "https://www.u-kari.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
# Import models so SQLAlchemy registers them
# -----------------------------------------
from db_utils.models import User, Order, Trip, OrderEvent

# -----------------------------------------
# Import Base and engine AFTER models
# -----------------------------------------
from db_utils.db import Base, engine

# -----------------------------------------
# Create tables
# -----------------------------------------
Base.metadata.create_all(bind=engine)

# -----------------------------------------
# Import routers (MATCHING YOUR ACTUAL FILES)
# -----------------------------------------

# Auth
from auth.auth_router import router as auth_router
from auth.me_router import router as me_router

# Admin
from routers.admin_dashboard import router as admin_dashboard_router
from routers.admin_disputes import router as admin_disputes_router
from routers.admin_payouts import router as admin_payouts_router
from routers.admin_timeline import router as admin_timeline_router

# Buyer / Traveler
from routers.buyer_app import router as buyer_app_router
from routers.traveler_app import router as traveler_app_router

# Core business logic
from routers.orders import router as orders_router
from routers.trips import router as trips_router
from routers.matching import router as matching_router
from routers.purchasing import router as purchasing_router
from routers.walmart_purchasing import router as walmart_purchasing_router

# Earnings
from routers.earnings import router as earnings_router
from routers.earnings_summary import router as earnings_summary_router
from routers.trip_earnings import router as trip_earnings_router

# Enforcement / Fraud / Recovery
from routers.enforcement import router as enforcement_router
from routers.fraud_admin import router as fraud_admin_router
from routers.recovery import router as recovery_router

# Ratings / Realtime / Profile
from routers.ratings import router as ratings_router
from routers.realtime import router as realtime_router
from routers.profile_router import router as profile_router

# Stripe
from routers.stripe_balance import router as stripe_balance_router
from routers.stripe_connect import router as stripe_connect_router
from routers.stripe_payout import router as stripe_payout_router
from routers.stripe_payout_history import router as stripe_payout_history_router
from routers.stripe_webhook import router as stripe_webhook_router

# Internal payouts engine
from routers.payouts_internal import router as payouts_internal_router

# Webhooks
from routers.webhook import router as webhook_router

# -----------------------------------------
# Register routers (CLEAN ORDER)
# -----------------------------------------

# Auth
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(me_router, prefix="/auth", tags=["Auth"])

# Admin
app.include_router(admin_dashboard_router, prefix="/admin/dashboard", tags=["Admin"])
app.include_router(admin_disputes_router, prefix="/admin/disputes", tags=["Admin"])
app.include_router(admin_payouts_router, prefix="/admin/payouts", tags=["Admin"])
app.include_router(admin_timeline_router, prefix="/admin/timeline", tags=["Admin"])

# Buyer / Traveler
app.include_router(buyer_app_router, prefix="/buyer", tags=["Buyer"])
app.include_router(traveler_app_router, prefix="/traveler", tags=["Traveler"])

# Core business logic
app.include_router(orders_router, prefix="/orders", tags=["Orders"])
app.include_router(trips_router, prefix="/trips", tags=["Trips"])
app.include_router(matching_router, prefix="/matching", tags=["Matching"])
app.include_router(purchasing_router, prefix="/purchasing", tags=["Purchasing"])
app.include_router(walmart_purchasing_router, prefix="/walmart", tags=["Purchasing"])

# Earnings
app.include_router(earnings_router, prefix="/earnings", tags=["Earnings"])
app.include_router(earnings_summary_router, prefix="/earnings/summary", tags=["Earnings"])
app.include_router(trip_earnings_router, prefix="/trip-earnings", tags=["Earnings"])

# Enforcement / Fraud / Recovery
app.include_router(enforcement_router, prefix="/enforcement", tags=["Enforcement"])
app.include_router(fraud_admin_router, prefix="/fraud", tags=["Fraud"])
app.include_router(recovery_router, prefix="/recovery", tags=["Recovery"])

# Ratings / Realtime / Profile
app.include_router(ratings_router, prefix="/ratings", tags=["Ratings"])
app.include_router(realtime_router, prefix="/realtime", tags=["Realtime"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])

# Stripe
app.include_router(stripe_balance_router, prefix="/stripe/balance", tags=["Stripe"])
app.include_router(stripe_connect_router, prefix="/stripe/connect", tags=["Stripe"])
app.include_router(stripe_payout_router, prefix="/stripe/payout", tags=["Stripe"])
app.include_router(stripe_payout_history_router, prefix="/stripe/payout-history", tags=["Stripe"])
app.include_router(stripe_webhook_router, prefix="/stripe/webhook", tags=["Stripe"])

# Internal payouts engine
app.include_router(payouts_internal_router, prefix="/payouts/internal", tags=["Payouts"])

# Webhooks
app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])

# -----------------------------------------
# Root endpoint
# -----------------------------------------
@app.get("/")
def root():
    return {"status": "ok"}




