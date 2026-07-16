from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import Order, User
from utils.auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"]
)

# ---------------------------------------------------------
# 1. View all orders
# ---------------------------------------------------------
@router.get("/orders")
def get_all_orders(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    orders = db.query(Order).order_by(Order.id.desc()).all()

    return {
        "status": "success",
        "orders": [
            {
                "order_id": o.id,
                "buyer_id": o.buyer_id,
                "traveler_id": o.traveler_id,
                "status": o.status,
                "price": o.item_price_cents,
                "delivery_location": o.delivery_location,
            }
            for o in orders
        ],
    }


# ---------------------------------------------------------
# 2. View all travelers
# ---------------------------------------------------------
@router.get("/travelers")
def get_travelers(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    travelers = db.query(User).filter(User.role == "traveler").all()

    return {
        "status": "success",
        "travelers": [
            {
                "id": t.id,
                "name": t.name,
                "rating": t.rating,
                "reliability_score": t.reliability_score,
                "on_time": t.on_time_deliveries,
                "late": t.late_deliveries,
                "cancellations": t.cancellation_count,
                "flight_cancels": t.flight_cancel_count,
                "status": t.status,
            }
            for t in travelers
        ],
    }


# ---------------------------------------------------------
# 3. View all buyers
# ---------------------------------------------------------
@router.get("/buyers")
def get_buyers(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    buyers = db.query(User).filter(User.role == "buyer").all()

    return {
        "status": "success",
        "buyers": [
            {
                "id": b.id,
                "name": b.name,
                "chargebacks": b.chargeback_count,
                "returns": b.return_count,
                "status": b.status,
            }
            for b in buyers
        ],
    }


# ---------------------------------------------------------
# 4. View banned users
# ---------------------------------------------------------
@router.get("/banned")
def get_banned_users(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    banned = db.query(User).filter(User.status == "banned").all()

    return {
        "status": "success",
        "banned_users": [
            {
                "id": u.id,
                "name": u.name,
                "role": u.role,
                "chargebacks": u.chargeback_count,
                "returns": u.return_count,
            }
            for u in banned
        ],
    }


# ---------------------------------------------------------
# 5. Trigger reroute
# ---------------------------------------------------------
@router.post("/reroute/{order_id}")
def admin_reroute(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.traveler_id = None
    order.status = "rerouted"
    db.commit()

    return {"status": "success", "message": "Order rerouted"}


# ---------------------------------------------------------
# 6. Trigger repurchase
# ---------------------------------------------------------
@router.post("/repurchase/{order_id}")
def admin_repurchase(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "reordered"
    db.commit()

    return {"status": "success", "message": "Order repurchased"}


# ---------------------------------------------------------
# 7. Trigger auto-assign
# ---------------------------------------------------------
@router.post("/auto-assign/{order_id}")
def admin_auto_assign(order_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(db, token)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    from utils.matching_engine import find_best_traveler

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    trip = find_best_traveler(db, order)
    if not trip:
        return {"status": "pending", "message": "No eligible travelers available"}

    order.traveler_id = trip.traveler_id
    order.status = "accepted"
    db.commit()

    return {
        "status": "success",
        "message": "Traveler assigned",
        "traveler_id": trip.traveler_id,
    }

