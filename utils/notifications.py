# utils/notifications.py

from typing import Optional
from db_utils.models import User
from utils.event_logger import log_event

# Placeholder SMS + Email senders (integrate Twilio/SendGrid later)
def send_sms(phone: str, message: str):
    print(f"[SMS to {phone}] {message}")


def send_email(email: str, subject: str, body: str):
    print(f"[EMAIL to {email}] {subject} - {body}")


def notify_user(
    db,
    user: User,
    order_id: int,
    title: str,
    message: str,
    event_type: str,
):
    """
    Unified notification dispatcher:
    - Logs event (in-app)
    - Sends SMS if phone exists
    - Sends email if email exists
    """

    # In-app event log
    log_event(
        db=db,
        order_id=order_id,
        event_type=event_type,
        description=message,
    )

    # SMS
    if user.phone:
        send_sms(user.phone, f"{title}: {message}")

    # Email
    if user.email:
        send_email(user.email, title, message)

    return True
