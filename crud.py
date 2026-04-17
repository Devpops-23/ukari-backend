from sqlalchemy.orm import Session
from models import Traveler
from database import get_db



def get_traveler_by_email(db: Session, email: str):
    return db.query(Traveler).filter(Traveler.email == email).first()


def get_traveler_by_id(db: Session, traveler_id: int):
    return db.query(Traveler).filter(Traveler.id == traveler_id).first()


def save_stripe_account(db: Session, traveler_id: int, account_id: str):
    traveler = get_traveler_by_id(db, traveler_id)
    if not traveler:
        return None

    traveler.stripe_account_id = account_id
    db.commit()
    db.refresh(traveler)
    return traveler
