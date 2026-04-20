# Notify buyer when order is created
from fastapi import HTTPException

from db_utils import db
from db_utils.models import Order, User
from utils.notifications import notify_user


notify_user(
    db=db,
    user=buyer,
    order_id=Order.id,
    title="Order Created",
    message="Your order has been created and is awaiting traveler assignment.",
    event_type="order_created",
)

if buyer.status == "banned":
    raise HTTPException(
        status_code=403,
        detail="Your account has been restricted due to repeated violations."
    )

if buyer.status == "banned":
    raise HTTPException(
        status_code=403,
        detail="Your account is no longer allowed to place orders."
    )


# Fetch traveler AFTER buyer confirms delivery
traveler = db.query(User).filter(User.id == Order.traveler_id).first()

# Notify traveler that buyer confirmed delivery
notify_user(
    db=db,
    user=traveler,
    order_id=Order.id,
    title="Delivery Confirmed",
    message="Buyer confirmed delivery. Your payout will be released.",
    event_type="delivery_confirmed",
)
# On-time vs late delivery tracking
if Order.delivered_at <= Order.delivery_deadline:
    traveler.on_time_deliveries += 1
else:
    traveler.late_deliveries += 1

db.commit()

