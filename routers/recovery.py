# routers/recovery.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime

from db_utils import db
from db_utils.db import get_db
from db_utils.models import Order, User, Trip
from routers import traveler
from utils.auth import get_current_user
from utils.event_logger import log_event
from utils.marketplace_client import get_marketplace_client
from utils.matching_engine import find_best_traveler
from utils.notifications import notify_user

router = APIRouter(prefix="/recovery", tags=["Order Recovery"])


# ---------------------------------------------------------
# 1. Traveler reports flight cancellation (uploads proof)
# ---------------------------------------------------------
@router.post("/flight-cancelled/{order_id}")
def report_flight_cancelled(
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

    proof_filename = f"flight_cancel_{order.id}_{int(datetime.utcnow().timestamp())}.jpg"
    with open(proof_filename, "wb") as f:
        f.write(file.file.read())

    order.status = "flight_cancelled"
    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="flight_cancelled",
        description=f"Traveler {traveler.id} reported flight cancellation",
    )

    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    if buyer:
        notify_user(
            db=db,
            user=buyer,
            order_id=order.id,
            title="Delivery Delay",
            message="Traveler flight was cancelled. U-KARI is re-routing your order.",
            event_type="flight_cancelled",
        )

    return {
        "status": "success",
        "message": "Flight cancellation reported. Please return the item to the store.",
        "proof_saved_as": proof_filename,
    }


# ---------------------------------------------------------
# 2. Traveler confirms item returned to store
# ---------------------------------------------------------
@router.post("/returned/{order_id}")
def confirm_returned(order_id: int, token: str, db: Session = Depends(get_db)):
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

    if order.status != "flight_cancelled":
        raise HTTPException(status_code=400, detail="Order is not in flight_cancelled state")

    order.status = "returned_to_store"
    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="returned_to_store",
        description=f"Traveler {traveler.id} returned item to store",
    )

    return {
        "status": "success",
        "message": "Item marked as returned to store.",
    }


# ---------------------------------------------------------
# 3. Admin confirms refund received from store
# ---------------------------------------------------------
@router.post("/refund-received/{order_id}")
def refund_received(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "returned_to_store":
        raise HTTPException(status_code=400, detail="Order is not ready for refund confirmation")

    order.status = "refund_received"
    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="refund_received",
        description="Refund from store received by U-KARI",
    )

    return {
        "status": "success",
        "message": "Refund confirmed.",
    }

buyer = db.query(User).filter(User.id == Order.buyer_id).first()

buyer.return_count += 1

if buyer.return_count >= 2:
    buyer.status = "banned"

db.commit()

# ---------------------------------------------------------
# 4. Admin repurchases item (auto)
# ---------------------------------------------------------
@router.post("/repurchase/{order_id}")
def repurchase_item(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "refund_received":
        raise HTTPException(status_code=400, detail="Order is not ready for repurchase")

    client = get_marketplace_client()
    _ = client.get_product_details(order.product_source, order.product_sku)

    order.status = "reordered"
    order.purchase_status = "pending"
    order.shipment_status = "pending"
    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="order_reordered",
        description="Item repurchased after refund",
    )

    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    if buyer:
        notify_user(
            db=db,
            user=buyer,
            order_id=order.id,
            title="Order Repurchased",
            message="Your item has been repurchased and will be re-assigned to a new traveler.",
            event_type="order_reordered",
        )

    return {
        "status": "success",
        "message": "Item repurchased. Ready for re-routing.",
    }


# ---------------------------------------------------------
# 5. Re-route order to new traveler (clear old traveler)
# ---------------------------------------------------------
@router.post("/reroute/{order_id}")
def reroute_order(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ["reordered", "refund_received"]:
        raise HTTPException(status_code=400, detail="Order is not ready for rerouting")

    order.traveler_id = None
    order.status = "rerouted"
    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="order_rerouted",
        description="Order re-routed to new traveler",
    )

    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    if buyer:
        notify_user(
            db=db,
            user=buyer,
            order_id=order.id,
            title="Order Re-Routed",
            message="Your order has been re-routed and will be assigned to a new traveler.",
            event_type="order_rerouted",
        )

    return {
        "status": "success",
        "message": "Order re-routed. Matching engine will assign a new traveler.",
    }


# ---------------------------------------------------------
# 6. Auto-assign new traveler after reroute
# ---------------------------------------------------------
@router.post("/auto-assign/{order_id}")
def auto_assign(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ["rerouted", "reordered"]:
        raise HTTPException(status_code=400, detail="Order is not ready for auto-assignment")

    trip = find_best_traveler(db, order)
    if not trip:
        return {
            "status": "pending",
            "message": "No available travelers yet. System will retry.",
        }

    order.traveler_id = trip.traveler_id
    order.status = "accepted"
    order.accepted_at = datetime.utcnow()
    order.traveler_arrived_at = None
    order.delivery_deadline = None

    db.commit()
    db.refresh(order)

    log_event(
        db=db,
        order_id=order.id,
        event_type="traveler_assigned",
        description=f"Order auto-assigned to traveler {trip.traveler_id}",
    )

    traveler = db.query(User).filter(User.id == trip.traveler_id).first()
    if traveler:
        notify_user(
            db=db,
            user=traveler,
            order_id=order.id,
            title="New Delivery Assigned",
            message=f"You have been assigned a re-routed delivery to {order.delivery_location}.",
            event_type="traveler_assigned",
        )

    return {
        "status": "success",
        "message": "Order automatically assigned to new traveler",
        "order_id": order.id,
        "traveler_id": trip.traveler_id,
    }

from utils.fraud_engine import calculate_risk_score, flag_order

risk = calculate_risk_score(traveler, Order)
if risk >= 50:
    flag_order(db, Order, "High-risk traveler assignment blocked")
    "return" {
        "status": "blocked",
        "message": "Order flagged due to high-risk traveler",
    }

# Matching engine already enforces 2-week rule
trip = find_best_traveler(db, Order)
if not trip:
    return {
        "status": "pending",
        "message": "No eligible travelers (2-week rule). System will retry.",
    }

# ---------------------------------------------------------
# 7. CRON: Retry auto-assignment for all rerouted/reordered orders
# ---------------------------------------------------------
@router.post("/auto-assign/retry")
def retry_auto_assignments(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    pending_orders = (
        db.query(Order)
        .filter(Order.status.in_(["rerouted", "reordered"]))
        .all()
    )

    results = []

    for order in pending_orders:
        trip = find_best_traveler(db, order)
        if not trip:
            results.append(
                {
                    "order_id": order.id,
                    "status": "no_traveler_available",
                }
            )
            continue

        order.traveler_id = trip.traveler_id
        order.status = "accepted"
        order.accepted_at = datetime.utcnow()
        order.traveler_arrived_at = None
        order.delivery_deadline = None

        db.commit()
        db.refresh(order)

        log_event(
            db=db,
            order_id=order.id,
            event_type="traveler_assigned",
            description=f"Order auto-assigned to traveler {trip.traveler_id}",
        )

        traveler = db.query(User).filter(User.id == trip.traveler_id).first()
        if traveler:
            notify_user(
                db=db,
                user=traveler,
                order_id=order.id,
                title="New Delivery Assigned",
                message=f"You have been assigned a re-routed delivery to {order.delivery_location}.",
                event_type="traveler_assigned",
            )

        results.append(
            {
                "order_id": order.id,
                "traveler_id": trip.traveler_id,
                "status": "assigned",
            }
        )

    return {
        "status": "success",
        "results": results,
    }

buyer = db.query(User).filter(User.id == Order.buyer_id).first()

notify_user(
    db=db,
    user=buyer,
    order_id=Order.id,
    title="Delivery Delay",
    message="Traveler flight was cancelled. U-KARI is re-routing your order.",
    event_type="flight_cancelled",
)

from utils.fraud_engine import verify_flight_cancellation, flag_order

if not verify_flight_cancellation(proof_filename):
    flag_order(db, Order, "Invalid flight cancellation proof")
    raise HTTPException(status_code=400, detail="Invalid flight cancellation proof")

traveler.flight_cancel_count += 1
db.commit()

traveler.flight_cancel_count += 1
db.commit()
