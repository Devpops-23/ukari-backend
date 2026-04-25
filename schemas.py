from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------
# TRAVELER OUT (User with role="traveler")
# ---------------------------------------------------------
class TravelerOut(BaseModel):
    id: int
    name: str
    email: str
    rating: float
    reliability_score: float

    class Config:
        orm_mode = True


# ---------------------------------------------------------
# TRIP OUT
# ---------------------------------------------------------
class TripOut(BaseModel):
    id: int
    origin: str
    destination: str
    travel_date: datetime
    status: str
    total_earned: float

    class Config:
        orm_mode = True


# ---------------------------------------------------------
# ORDER OUT
# ---------------------------------------------------------
class OrderOut(BaseModel):
    id: int
    status: str
    amount_earned: float
    delivered_at: Optional[datetime]

    class Config:
        orm_mode = True
