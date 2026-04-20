from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from db_utils.models import Traveler, Order

router = APIRouter(prefix="/earnings", tags=["Earnings Summary"])


def get_current_user(db: Session, token: str):
    user = db.query(Traveler).filter(Traveler.access_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/summary")
def earnings_summary(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    orders = db.query(Order).filter(Order.traveler_id == user.id).all()

    now = datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day)
    start_of_week = start_of_day - timedelta(days=now.weekday())
    start_of_month = datetime(now.year, now.month, 1)

    today = 0
    week = 0
    month = 0
    lifetime = 0

    for o in orders:
        lifetime += o.amount_earned

        if o.trip.date >= start_of_day:
            today += o.amount_earned

        if o.trip.date >= start_of_week:
            week += o.amount_earned

        if o.trip.date >= start_of_month:
            month += o.amount_earned

    return {
        "today": today,
        "week": week,
        "month": month,
        "lifetime": lifetime
    }
