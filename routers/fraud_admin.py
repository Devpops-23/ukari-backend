# routers/fraud_admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_utils.db import get_db
from db_utils.models import Order, User
from utils.auth import get_current_user

router = APIRouter(prefix="/fraud", tags=["Fraud Admin"])


@router.get("/flagged-orders")
def flagged_orders(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    orders = db.query(Order).filter(Order.flagged == True).all()

    return {
        "status": "success",
        "count": len(orders),
        "orders": [
            {
                "order_id": o.id,
                "buyer_id": o.buyer_id,
                "traveler_id": o.traveler_id,
                "status": o.status,
            }
            for o in orders
        ],
    }
