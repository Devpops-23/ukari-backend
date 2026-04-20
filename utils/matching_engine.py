# utils/matching_engine.py

from sqlalchemy.orm import Session
from datetime import datetime
from db_utils.models import Trip, Order


def find_best_traveler(db: Session, order: Order):
    """
    Finds the best traveler for a rerouted or new order.
    Criteria:
    - Destination matches
    - Trip is active
    - Traveler has capacity
    - Traveler is not the previous traveler
    """

    candidates = (
        db.query(Trip)
        .filter(
            Trip.destination == order.delivery_location,
            Trip.status == "active",
            Trip.max_weight >= order.item_price,
        )
        .order_by(Trip.travel_date.asc())
        .all()
    )

    if not candidates:
        return None

    # Pick earliest traveler going to destination
    return candidates[0]

# utils/matching_engine.py

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from db_utils.models import Trip, Order


def find_best_traveler(db: Session, order: Order):
    """
    Finds the best traveler for a rerouted or new order.
    Enforces:
    - Destination match
    - Active trip
    - Weight capacity
    - Departure at least 14 days AFTER expected package arrival
    """

    # Assume marketplace shipping takes 3–5 days
    expected_arrival = datetime.utcnow() + timedelta(days=5)
    min_required_date = expected_arrival + timedelta(days=14)

    candidates = (
        db.query(Trip)
        .filter(
            Trip.destination == order.delivery_location,
            Trip.status == "active",
            Trip.max_weight >= order.item_price,
            Trip.travel_date >= min_required_date,   # <-- 2 WEEK RULE
        )
        .order_by(Trip.travel_date.asc())
        .all()
    )

    if not candidates:
        return None

    return candidates[0]
