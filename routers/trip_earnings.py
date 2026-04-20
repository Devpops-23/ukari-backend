from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Order

router = APIRouter(prefix="/earnings", tags=["Trip Earnings"])

@router.get("/trips/{traveler_id}")
def get_trip_earnings(traveler_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.traveler_id == traveler_id).all()

    total = sum(o.amount_earned for o in orders)
    pending = sum(o.amount_earned for o in orders if o.status == "pending")
    completed = sum(o.amount_earned for o in orders if o.status == "delivered")

    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "orders": [
            {
                "id": o.id,
                "amount": o.amount_earned,
                "status": o.status
            }
            for o in orders
        ]
    }
