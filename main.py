# -------------------------------
# Import routers (CORRECTED)
# -------------------------------

# Auth
from auth.auth_router import router as auth_router
from auth.me_router import router as me_router

# Admin
from routers.admin_dashboard import router as admin_dashboard_router
from routers.admin_disputes import router as admin_disputes_router
from routers.admin_payouts import router as admin_payouts_router
from routers.admin_timeline import router as admin_timeline_router

# Buyer / Traveler Apps
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


# -------------------------------
# Register routers (CLEAN ORDER)
# -------------------------------

# Auth
app.include_router(admin_dashboard_router)
app.include_router(admin_disputes_router)
app.include_router(admin_payouts_router)
app.include_router(admin_timeline_router)

app.include_router(buyer_app_router)
app.include_router(traveler_app_router)

app.include_router(orders_router)
app.include_router(trips_router)
app.include_router(matching_router)
app.include_router(purchasing_router)
app.include_router(walmart_purchasing_router)

app.include_router(earnings_router)
app.include_router(earnings_summary_router)
app.include_router(trip_earnings_router)

app.include_router(enforcement_router)
app.include_router(fraud_admin_router)
app.include_router(recovery_router)

app.include_router(ratings_router)
app.include_router(realtime_router)
app.include_router(profile_router)

app.include_router(stripe_balance_router)
app.include_router(stripe_connect_router)
app.include_router(stripe_payout_router)
app.include_router(stripe_payout_history_router)
app.include_router(stripe_webhook_router)

app.include_router(payouts_internal_router)

app.include_router(webhook_router)



