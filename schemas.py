from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class TravelerOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    stripe_account_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    default_payment_method: Optional[str] = None
    account_verified: Optional[bool] = None
    stripe_charges_enabled: Optional[bool] = None
    stripe_payouts_enabled: Optional[bool] = None

    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None

    rating: Optional[float] = None
    reliability_score: Optional[float] = None
    on_time_deliveries: Optional[int] = None
    late_deliveries: Optional[int] = None
    cancellation_count: Optional[int] = None
    flight_cancel_count: Optional[int] = None
    chargeback_count: Optional[int] = None
    return_count: Optional[int] = None

    status: Optional[str] = None
    created_at: Optional[datetime] = None

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
