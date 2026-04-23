from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db_utils.db import get_db
from db_utils.models import User, Order, Trip, OrderEvent
from utils.auth import get_current_user

router = APIRouter()



# ---------------------------------------------------------
# TRAVELER ACCEPTS AN ORDER (STEP 10)
# ---------------------------------------------------------
@router.post("/{order_id}/accept")
def accept_order(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can accept orders")

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not available for acceptance")

    order.traveler_id = user.id
    order.accepted_at = datetime.utcnow()
    order.status = "accepted"

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Order accepted",
        "order_id": order.id,
        "traveler_id": user.id,
        "accepted_at": order.accepted_at.isoformat(),
    }


# ---------------------------------------------------------
# TRAVELER ASSIGNS ORDER TO A TRIP (NEW FOR STEP 11)
# ---------------------------------------------------------
@router.post("/{order_id}/assign-trip/{trip_id}")
def assign_order_to_trip(order_id: int, trip_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can assign orders to trips")

    # Validate order
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.traveler_id == user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.status not in ["accepted", "in_transit", "delivered_to_traveler"]:
        raise HTTPException(status_code=400, detail="Order cannot be assigned at this stage")

    # Validate trip
    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.traveler_id == user.id)
        .first()
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or unauthorized")

    if trip.status != "active":
        raise HTTPException(status_code=400, detail="Cannot assign orders to a completed or cancelled trip")

    # Assign order to trip
    order.trip_id = trip.id

    # Update trip earnings
    trip.total_earned += order.traveler_fee or 0

    db.commit()
    db.refresh(order)
    db.refresh(trip)

    return {
        "status": "success",
        "message": "Order assigned to trip",
        "order_id": order.id,
        "trip_id": trip.id,
        "trip_total_earned": trip.total_earned,
    }


# ---------------------------------------------------------
# GET AVAILABLE ORDERS (Traveler)
# ---------------------------------------------------------
@router.get("/available")
def get_available_orders(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view available orders")

    orders = (
        db.query(Order)
        .filter(Order.status == "pending")
        .order_by(Order.id.desc())
        .all()
    )

    formatted = []
    for o in orders:
        formatted.append({
            "order_id": o.id,
            "store_name": o.store_name,
            "amount": o.amount,
            "pickup_location": o.pickup_location,
            "delivery_location": o.delivery_location,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return {"status": "success", "orders": formatted}


# ---------------------------------------------------------
# TRAVELER CONFIRMS PACKAGE RECEIVED FROM AMAZON/WALMART
# ---------------------------------------------------------
@router.post("/{order_id}/traveler-confirm-received")
def traveler_confirm_received(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can confirm package receipt")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.traveler_id == user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.shipment_status != "in_transit":
        raise HTTPException(status_code=400, detail="Order is not marked as in transit")

    order.shipment_status = "delivered_to_traveler"
    order.traveler_received_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Traveler confirmed package received",
        "order_id": order.id,
        "shipment_status": order.shipment_status,
        "traveler_received_at": order.traveler_received_at.isoformat(),
    }


# ---------------------------------------------------------
# TRAVELER UPLOADS DELIVERY PROOF
# ---------------------------------------------------------
@router.post("/{order_id}/upload-proof")
def upload_delivery_proof(
    order_id: int,
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can upload proof")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.traveler_id == user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.shipment_status != "delivered_to_traveler":
        raise HTTPException(status_code=400, detail="Traveler has not confirmed receiving the package")

    filename = f"proof_{order_id}_{int(datetime.utcnow().timestamp())}.jpg"
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())

    order.proof_photo_filename = filename
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Delivery proof uploaded",
        "file": filename,
    }


# ---------------------------------------------------------
# BUYER CONFIRMS DELIVERY
# ---------------------------------------------------------
@router.post("/{order_id}/buyer-confirm")
def buyer_confirm_delivery(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can confirm delivery")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.buyer_id == user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.status != "delivered":
        raise HTTPException(status_code=400, detail="Order has not been delivered yet")

    order.status = "buyer_confirmed"
    order.buyer_confirmed_at = datetime.utcnow()
    order.amount_earned = order.traveler_fee

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "message": "Buyer confirmed delivery",
        "order_id": order.id,
    }


# ---------------------------------------------------------
# DISPUTE SYSTEM (unchanged from Step 8)
# ---------------------------------------------------------
@router.post("/{order_id}/open-dispute")
def open_dispute(order_id: int, reason: str, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can open disputes")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.buyer_id == user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or unauthorized")

    if order.dispute_status is not None:
        raise HTTPException(status_code=400, detail="Dispute already exists")

    order.dispute_reason = reason
    order.dispute_status = "open"
    order.dispute_created_at = datetime.utcnow()
    order.status = "disputed"

    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Dispute opened", "order_id": order.id}


@router.post("/{order_id}/resolve-dispute")
def resolve_dispute(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.dispute_status = "resolved"
    order.status = "buyer_confirmed"

    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Dispute resolved", "order_id": order.id}


@router.post("/{order_id}/reject-dispute")
def reject_dispute(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.dispute_status = "rejected"
    order.status = "buyer_confirmed"

    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Dispute rejected", "order_id": order.id}


# ---------------------------------------------------------
# MARK ORDER AS PAID
# ---------------------------------------------------------
@router.post("/{order_id}/mark-paid")
def mark_order_paid(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "buyer_confirmed":
        raise HTTPException(status_code=400, detail="Order is not ready for payout")

    order.status = "paid"
    order.paid_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return {"status": "success", "message": "Order marked as paid", "order_id": order.id}


# ---------------------------------------------------------
# ADMIN DASHBOARD — VIEW ALL ORDERS
# ---------------------------------------------------------
@router.get("/admin/all")
def admin_get_all_orders(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    orders = db.query(Order).order_by(Order.id.desc()).all()

    formatted = []
    for o in orders:
        formatted.append({
            "order_id": o.id,
            "buyer_id": o.buyer_id,
            "traveler_id": o.traveler_id,
            "product_source": o.product_source,
            "product_url": o.product_url,
            "purchase_status": o.purchase_status,
            "shipment_status": o.shipment_status,
            "tracking_number": o.shipment_tracking_number,
            "carrier": o.shipment_carrier,
            "status": o.status,
            "dispute_status": o.dispute_status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return {"status": "success", "orders": formatted}


# ---------------------------------------------------------
# ADMIN — FULL ORDER DETAILS VIEW
# ---------------------------------------------------------
@router.get("/admin/details/{order_id}")
def admin_order_details(order_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    traveler = db.query(User).filter(User.id == order.traveler_id).first()

    return {
        "status": "success",
        "order": {
            "order_id": order.id,
            "product_source": order.product_source,
            "product_url": order.product_url,
            "product_sku": order.product_sku,
            "item_price": order.item_price,
            "platform_fee": order.platform_fee,
            "traveler_fee": order.traveler_fee,
            "total_charged": order.total_charged,
            "purchase_status": order.purchase_status,
            "purchase_reference": order.purchase_reference,
            "shipment_status": order.shipment_status,
            "tracking_number": order.shipment_tracking_number,
            "carrier": order.shipment_carrier,
            "traveler_received_at": order.traveler_received_at.isoformat() if order.traveler_received_at else None,
            "delivery_status": order.status,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "buyer_confirmed_at": order.buyer_confirmed_at.isoformat() if order.buyer_confirmed_at else None,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "proof_photo_filename": order.proof_photo_filename,
            "dispute_status": order.dispute_status,
            "dispute_reason": order.dispute_reason,
            "dispute_created_at": order.dispute_created_at.isoformat() if order.dispute_created_at else None,
        },
        "buyer": {
            "id": buyer.id,
            "email": buyer.email,
        } if buyer else None,
        "traveler": {
            "id": traveler.id,
            "email": traveler.email,
            "shipping_address": {
                "line1": traveler.shipping_address_line1,
                "line2": traveler.shipping_address_line2,
                "city": traveler.shipping_city,
                "state": traveler.shipping_state,
                "postal_code": traveler.shipping_postal_code,
                "country": traveler.shipping_country,
            } if traveler else None,
        } if traveler else None,
    }


# ---------------------------------------------------------
# TRAVELER EARNINGS DASHBOARD
# ---------------------------------------------------------
@router.get("/traveler/earnings")
def traveler_earnings(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view earnings")

    orders = (
        db.query(Order)
        .filter(Order.traveler_id == user.id)
        .order_by(Order.id.desc())
        .all()
    )

    total_earned = sum(o.amount_earned for o in orders)
    pending = sum(o.traveler_fee for o in orders if o.status == "buyer_confirmed")
    disputed = [o.id for o in orders if o.status == "disputed"]
    completed = [o.id for o in orders if o.status == "paid"]

    per_order = []
    for o in orders:
        per_order.append({
            "order_id": o.id,
            "traveler_fee": o.traveler_fee,
            "amount_earned": o.amount_earned,
            "status": o.status,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        })

    return {
        "status": "success",
        "traveler_id": user.id,
        "total_earned": total_earned,
        "pending_payout": pending,
        "completed_orders": completed,
        "disputed_orders": disputed,
        "orders": per_order,
    }


# ---------------------------------------------------------
# TRAVELER TRIP EARNINGS SUMMARY
# ---------------------------------------------------------
@router.get("/traveler/trips")
def traveler_trip_earnings(token: str, db: Session = Depends(get_db)):
    user = get_current_user(db, token)

    if user.role != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers can view trip earnings")

    trips = (
        db.query(Trip)
        .filter(Trip.traveler_id == user.id)
        .order_by(Trip.id.desc())
        .all()
    )

    formatted = []
    for t in trips:
        formatted.append({
            "trip_id": t.id,
            "origin": t.origin,
            "destination": t.destination,
            "travel_date": t.travel_date.isoformat(),
            "total_earned": t.total_earned,
            "status": t.status,
        })

    return {"status": "success", "trips": formatted}
    log_event(
        db=db,
        order_id=order.id,
        event_type="delivery_confirmed",
        description="Buyer confirmed delivery",
)












    
