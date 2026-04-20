# utils/event_logger.py

from sqlalchemy.orm import Session
from db_utils.models import OrderEvent


def log_event(db: Session, order_id: int, event_type: str, description: str):
    event = OrderEvent(
        order_id=order_id,
        event_type=event_type,
        description=description,
    )
    db.add(event)
    db.commit()
