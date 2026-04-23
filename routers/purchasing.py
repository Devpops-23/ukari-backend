from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user

router = APIRouter()



# ---------------------------------------------------------
# ADMIN: PREPARE VIRTUAL CARD PURCHASE FOR AN ORDER
# ---------------------------------------------------------
@router.post("/prepare/{order_id}")
def prepare_purchase(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.purchase_status not in ["pending", "failed"]:
        raise HTTPException(status_code=400, detail="Order is not ready for purchase")

    if not order.product_source:
        raise HTTPException(status_code=400, detail="Order missing product_source")

    # Amount to charge card = item_price + marketplace shipping (if any)
    # Platform fee + traveler fee stay in Stripe balance.
    purchase_amount_cents = int(round(order.item_price * 100))

    auth_info = create_issuing_authorization(
        source=order.product_source,
        amount_cents=purchase_amount_cents,
        merchant_name=order.product_source,
        order_id=order.id,
    )

    # Mark order as "purchase_in_progress"
    order.purchase_status = "in_progress"
    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Virtual card prepared for marketplace purchase",
        "order_id": order.id,
        "card": auth_info,
    }


# ---------------------------------------------------------
# ADMIN: CONFIRM PURCHASE COMPLETED (AFTER USING CARD)
# ---------------------------------------------------------
@router.post("/confirm/{order_id}")
def confirm_purchase(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.purchase_status != "in_progress":
        raise HTTPException(status_code=400, detail="Order is not in purchase_in_progress state")

    purchase_amount_cents = int(round(order.item_price * 100))

    tx = record_issuing_transaction(
        order_id=order.id,
        source=order.product_source,
        amount_cents=purchase_amount_cents,
        merchant_name=order.product_source,
    )

    order.purchase_status = "completed"
    order.shipment_status = "in_transit"
    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Marketplace purchase confirmed and shipment in transit",
        "order_id": order.id,
        "transaction": tx,
    }
from utils.event_logger import log_event

log_event(
    db=db,
    order_id=order.id,
    event_type="purchase_completed",
    description=f"Marketplace purchase completed for {order.product_source}",
)
