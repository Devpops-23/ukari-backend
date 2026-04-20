# utils/fraud_engine.py

from datetime import datetime
from db_utils.models import User, Order
from utils.event_logger import log_event


def verify_delivery_photo(photo_path: str) -> bool:
    """
    Placeholder for:
    - Face detection
    - Package detection
    - Anti-spoofing
    """
    return True


def verify_flight_cancellation(photo_path: str) -> bool:
    """
    Placeholder for:
    - OCR text detection
    - Airline cancellation screen detection
    """
    return True


def calculate_risk_score(user: User, order: Order) -> int:
    """
    Simple rule-based risk scoring.
    Later: replace with ML model.
    """
    score = 0

    # New traveler account
    if (datetime.utcnow() - user.created_at).days < 7:
        score += 20

    # Multiple cancellations
    if user.cancellation_count > 3:
        score += 30

    # Multiple flight cancellations
    if user.flight_cancel_count > 2:
        score += 40

    # High-value orders
    if order.item_price > 500:
        score += 10

    return score


def flag_order(db, order: Order, reason: str):
    order.flagged = True
    db.commit()

    log_event(
        db=db,
        order_id=order.id,
        event_type="fraud_flag",
        description=f"Order flagged: {reason}",
    )

