from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./ukari.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_overdue_deliveries(now):
    # TODO: implement logic
    return []

def mark_delivery_failed(delivery_id: int):
    # TODO: implement logic
    pass

def mark_auto_charge_executed(delivery_id: int):
    # TODO: implement logic
    pass

