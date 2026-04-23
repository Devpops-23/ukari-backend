# db_utils/helpers.py

from datetime import datetime
from sqlalchemy.orm import Session
from db_utils.models import Order

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
        )
        .all()
    )


def mark_delivery_failed(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    order.status = "failed"
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


def mark_auto_charge_executed(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    db.commit()
    db.refresh(order)
    return order
