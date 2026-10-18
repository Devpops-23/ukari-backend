from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from db_utils.db import get_db
from db_utils.models import Order, User, Trip
from utils.auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
)


def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return user


# ---------------------------------------------------------
# 0. Admin System Summary (For Admin Dashboard)
# ---------------------------------------------------------
@router.get("/summary")
def get_admin_summary(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    total_orders = db.query(Order).count()
    active_orders = db.query(Order).filter(Order.status.in_(["pending", "accepted", "in_transit"])).count()
    completed_orders = db.query(Order).filter(Order.status.in_(["delivered", "buyer_confirmed", "paid"])).count()
    disputed_orders = db.query(Order).filter(Order.status == "disputed").count()

    total_travelers = db.query(User).filter(User.role == "traveler").count()
    total_buyers = db.query(User).filter(User.role == "buyer").count()

    return {
        "status": "success",
        "total_orders": total_orders,
        "active_orders": active_orders,
        "completed_orders": completed_orders,
        "disputes_count": disputed_orders,
        "total_travelers": total_travelers,
        "total_buyers": total_buyers,
    }


# ---------------------------------------------------------
# 1. View all orders
# ---------------------------------------------------------
@router.get("/orders")
def get_all_orders(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    orders = db.query(Order).order_by(Order.id.desc()).all()

    return {
        "status": "success",
        "orders": [
            {
                "id": o.id,
                "order_id": o.id,
                "item_name": o.item_name,
                "buyer_id": o.buyer_id,
                "traveler_id": o.traveler_id,
                "status": o.status,
                "price": o.item_price or (o.item_price_cents / 100.0 if o.item_price_cents else 0.0),
                "delivery_location": o.delivery_location,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
    }


# ---------------------------------------------------------
# 1b. View specific order
# ---------------------------------------------------------
@router.get("/orders/{order_id}")
def get_admin_order(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "status": "success",
        "order": {
            "id": order.id,
            "order_id": order.id,
            "item_name": order.item_name,
            "buyer_id": order.buyer_id,
            "traveler_id": order.traveler_id,
            "status": order.status,
            "price": order.item_price or (order.item_price_cents / 100.0 if order.item_price_cents else 0.0),
            "store_name": order.store_name or order.merchant_name,
            "delivery_location": order.delivery_location,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        },
    }


class UpdateOrderStatusRequest(BaseModel):
    status: str


@router.post("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    body: UpdateOrderStatusRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = body.status
    db.commit()
    db.refresh(order)

    return {"status": "success", "order_id": order.id, "new_status": order.status}


# ---------------------------------------------------------
# 2. View all users (combined)
# ---------------------------------------------------------
@router.get("/users")
def get_all_users(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id.desc()).all()

    return {
        "status": "success",
        "users": [
            {
                "id": u.id,
                "name": u.full_name,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "status": u.status,
                "rating": u.rating,
                "reliability_score": u.reliability_score,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": "success",
        "user": {
            "id": u.id,
            "name": u.full_name,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "rating": u.rating,
            "reliability_score": u.reliability_score,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        },
    }


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    u.status = "banned"
    db.commit()

    return {"status": "success", "message": f"User {user_id} has been banned"}


# ---------------------------------------------------------
# 3. View travelers
# ---------------------------------------------------------
@router.get("/travelers")
def get_travelers(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    travelers = db.query(User).filter(User.role == "traveler").all()

    return {
        "status": "success",
        "travelers": [
            {
                "id": t.id,
                "name": t.full_name,
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
# 4. View buyers
# ---------------------------------------------------------
@router.get("/buyers")
def get_buyers(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    buyers = db.query(User).filter(User.role == "buyer").all()

    return {
        "status": "success",
        "buyers": [
            {
                "id": b.id,
                "name": b.full_name,
                "chargebacks": b.chargeback_count,
                "returns": b.return_count,
                "status": b.status,
            }
            for b in buyers
        ],
    }


# ---------------------------------------------------------
# 5. View banned users
# ---------------------------------------------------------
@router.get("/banned")
def get_banned_users(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    banned = db.query(User).filter(User.status == "banned").all()

    return {
        "status": "success",
        "banned_users": [
            {
                "id": u.id,
                "name": u.full_name,
                "role": u.role,
                "chargebacks": u.chargeback_count,
                "returns": u.return_count,
            }
            for u in banned
        ],
    }


# ---------------------------------------------------------
# 6. Admin Actions (Reroute, Repurchase, Auto-assign)
# ---------------------------------------------------------
@router.post("/reroute/{order_id}")
def admin_reroute(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.traveler_id = None
    order.status = "rerouted"
    db.commit()

    return {"status": "success", "message": "Order rerouted"}


@router.post("/repurchase/{order_id}")
def admin_repurchase(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "reordered"
    db.commit()

    return {"status": "success", "message": "Order repurchased"}


@router.post("/auto-assign/{order_id}")
def admin_auto_assign(
    order_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
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
