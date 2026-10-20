from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field

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

    rating: Optional[float] = 0.0
    reliability_score: Optional[float] = 100.0
    on_time_deliveries: Optional[int] = 0
    late_deliveries: Optional[int] = 0
    cancellation_count: Optional[int] = 0
    flight_cancel_count: Optional[int] = 0
    chargeback_count: Optional[int] = 0
    return_count: Optional[int] = 0

    status: Optional[str] = "active"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# TRIP OUT
# ---------------------------------------------------------
class TripOut(BaseModel):
    id: int
    origin: str
    destination: str
    departure_date: Optional[datetime] = None
    arrival_date: Optional[datetime] = None
    travel_date: Optional[datetime] = None
    max_weight: Optional[float] = 20.0
    status: Optional[str] = "active"
    total_earned: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def trip_id(self) -> int:
        return self.id

    @computed_field
    @property
    def origin_city(self) -> str:
        return self.origin

    @computed_field
    @property
    def destination_city(self) -> str:
        return self.destination


# ---------------------------------------------------------
# ORDER OUT
# ---------------------------------------------------------
class OrderOut(BaseModel):
    id: int
    status: str = "pending"
    item_name: Optional[str] = ""
    item_price: Optional[float] = 0.0
    amount_earned: Optional[float] = 0.0
    delivered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
