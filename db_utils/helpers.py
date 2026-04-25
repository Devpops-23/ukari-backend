# db_utils/helpers.py

from datetime import datetime
from sqlalchemy.orm import Session
from db_utils.models import Order

# ---------------------------------------------------------
# U-KARI FEE ENGINE (FLAT FEES)
# ---------------------------------------------------------

PLATFORM_FEE = 10.0      # U-KARI revenue per item
TRAVELER_FEE = 25.0      # Traveler earnings per item

def calculate_fees(item_price: float):
    platform_fee = PLATFORM_FEE
    traveler_fee = TRAVELER_FEE
    total = item_price + platform_fee + traveler_fee

    return {
        "platform_fee": platform_fee,
        "traveler_fee": traveler_fee,
        "total_charged": total
    }


# ---------------------------------------------------------
# FIND OVERDUE DELIVERIES
# ---------------------------------------------------------
def get_overdue_deliveries(db: Session, now=None):
    if now is None:
        now = datetime.utcnow()

    return (
        db.query(Order)
        .filter(
            Order.delivery_deadline != None,
            Order.delivered_at == None,
            Order.delivery_deadline < now,
            Order.status.notin_(["paid", "refunded", "failed"]),
            Order.auto_charge_executed == False
        )
        .all()
    )


# ---------------------------------------------------------
# MARK DELIVERY AS FAILED
# ---------------------------------------------------------
def mark_delivery_failed(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    order.status = "failed"
    order.refunded_at = datetime.utcnow()
    order.auto_charge_executed = True  # prevent double-charging

    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------
# MARK AUTO-CHARGE AS EXECUTED
# ---------------------------------------------------------
def mark_auto_charge_executed(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    order.auto_charge_executed = True
    db.commit()
    db.refresh(order)
    return order

