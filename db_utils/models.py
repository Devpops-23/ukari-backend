from sqlalchemy import Column, Integer, String
from database import Base

class Traveler(Base):
    __tablename__ = "travelers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    stripe_account_id = Column(String, nullable=True)


