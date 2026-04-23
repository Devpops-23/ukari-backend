# routers/ratings.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime


from db_utils.models import Order, User
from utils.auth import get_current_user
from utils.event_logger import log_event
from utils.reliability import calculate_reliability

router = APIRouter(prefix="/ratings", tags=["Ratings"])


@router.post("/rate/{order_id}")
def rate_traveler(
    order_id: int,
    rating: int,
    comment: str = "",
    token: str = Depends(get_db),
    db: Session = Depends(get_db)
):
    buyer = get_current_user(db, token)

    if buyer.role != "buyer":
        raise HTTPException(status_code=403, detail="Buyer access only")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.buyer_id == buyer.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "paid":
        raise HTTPException(status_code=400, detail="Order must be completed before rating")

    traveler = db.query(User).filter(User.id == order.traveler_id).first()

    if not traveler:
        raise HTTPException(status_code=404, detail="Traveler not found")

    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Update traveler rating
    old_total = traveler.rating * traveler.rating_count
    new_total = old_total + rating
    traveler.rating_count += 1
    traveler.rating = new_total / traveler.rating_count

    # Update reliability score
    traveler.reliability_score = calculate_reliability(traveler)

    db.commit()
    db.refresh(traveler)

    # Log event
    log_event(
        db=db,
        order_id=order.id,
        event_type="traveler_rated",
        description=f"Traveler rated {rating} stars. Comment: {comment}",
    )

    return {
        "status": "success",
        "message": "Rating submitted",
        "traveler_rating": traveler.rating,
        "rating_count": traveler.rating_count,
        "reliability_score": traveler.reliability_score,
    }
