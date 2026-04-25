from sqlalchemy.orm import Session
from db_utils.models import User
from db_utils.db import get_db

# ---------------------------------------------------------
# U-KARI FEE ENGINE (FLAT FEES)
# ---------------------------------------------------------

PLATFORM_FEE = 10.0      # U-KARI revenue per item
TRAVELER_FEE = 25.0      # Traveler earnings per item

def calculate_fees(item_price: float):
    """
    Returns the platform fee, traveler fee, and total amount charged
    for a single item based on U-KARI's flat-fee model.
    """
    platform_fee = PLATFORM_FEE
    traveler_fee = TRAVELER_FEE
    total_charged = item_price + platform_fee + traveler_fee

    return {
        "platform_fee": platform_fee,
        "traveler_fee": traveler_fee,
        "total_charged": total_charged
    }


# ---------------------------------------------------------
# TRAVELER LOOKUP HELPERS
# ---------------------------------------------------------

def get_traveler_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email, User.role == "traveler").first()


def get_traveler_by_id(db: Session, traveler_id: int):
    return db.query(User).filter(User.id == traveler_id, User.role == "traveler").first()


# ---------------------------------------------------------
# SAVE STRIPE CONNECT ACCOUNT ID
# ---------------------------------------------------------

def save_stripe_account(db: Session, traveler_id: int, account_id: str):
    traveler = get_traveler_by_id(db, traveler_id)
    if not traveler:
        return None

    traveler.stripe_account_id = account_id
    db.commit()
    db.refresh(traveler)
    return traveler

