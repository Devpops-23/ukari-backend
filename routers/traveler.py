from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, User
from utils.auth import get_current_user
from utils.fraud_engine import verify_delivery_photo, flag_order

router = APIRouter(prefix="/traveler", tags=["Traveler App"])


@router.post("/order/{order_id}/arrived")
def traveler_arrived(order_id: int, token: str, db: Session = Depends(get_db)):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.traveler_id == traveler.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    now = datetime.utcnow()

    # Traveler arrival time
    order.traveler_arrived_at = now

    # 10-day delivery window starting tomorrow → 11 days from now at 23:59:59
    order.delivery_deadline = (now + timedelta(days=11)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Arrival confirmed. 10-day delivery window starts tomorrow.",
        "delivery_deadline": order.delivery_deadline.isoformat(),
    }


@router.post("/order/{order_id}/delivered")
async def traveler_mark_delivered(
    order_id: int,
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    traveler = get_current_user(db, token)

    if traveler.role != "traveler":
        raise HTTPException(status_code=403, detail="Traveler access only")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.traveler_id == traveler.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    # Save delivery photo
    os.makedirs("delivery_photos", exist_ok=True)
    photo_path = os.path.join(
        "delivery_photos",
        f"delivery_{order.id}_{int(datetime.utcnow().timestamp())}.jpg",
    )

    with open(photo_path, "wb") as f:
        f.write(await file.read())

    # Verify delivery photo (fraud engine)
    if not verify_delivery_photo(photo_path):
        flag_order(db, order, "Invalid delivery photo")
        raise HTTPException(
            status_code=400, detail="Delivery photo verification failed"
        )

    # Mark order as delivered
    order.delivered_at = datetime.utcnow()
    order.status = "delivered"

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Delivery marked as completed.",
        "order_id": order.id,
        "delivered_at": order.delivered_at.isoformat(),
    }

