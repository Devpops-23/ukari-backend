from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from db_utils.db import Base


# ---------------------------------------------------------
# USER MODEL
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="traveler")

    # Stripe fields
    stripe_account_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    default_payment_method = Column(String, nullable=True)
    account_verified = Column(Boolean, default=False)
    stripe_charges_enabled = Column(Boolean, default=False)
    stripe_payouts_enabled = Column(Boolean, default=False)

    # Traveler shipping address
    shipping_address_line1 = Column(String, nullable=True)
    shipping_address_line2 = Column(String, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_state = Column(String, nullable=True)
    shipping_postal_code = Column(String, nullable=True)
    shipping_country = Column(String, nullable=True)

    # Performance metrics
    rating = Column(Float, default=0.0)
    reliability_score = Column(Float, default=100.0)
    on_time_deliveries = Column(Integer, default=0)
    late_deliveries = Column(Integer, default=0)
    cancellation_count = Column(Integer, default=0)
    flight_cancel_count = Column(Integer, default=0)

    # Fraud counters
    chargeback_count = Column(Integer, default=0)
    return_count = Column(Integer, default=0)

    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trips = relationship("Trip", back_populates="traveler", cascade="all, delete-orphan")
    traveler_orders = relationship("Order", foreign_keys="Order.traveler_id", back_populates="traveler")
    buyer_orders = relationship("Order", foreign_keys="Order.buyer_id", back_populates="buyer")


# ---------------------------------------------------------
# TRIP MODEL
# ---------------------------------------------------------
class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_date = Column(DateTime, nullable=False)
    arrival_date = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    traveler = relationship("User", back_populates="trips")
    orders = relationship("Order", back_populates="trip")


# ---------------------------------------------------------
# ORDER MODEL
# ---------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)

    item_name = Column(String, nullable=False)
    item_price = Column(Float, nullable=False)
    store_name = Column(String, nullable=False)
    pickup_location = Column(String, nullable=False)
    delivery_location = Column(String, nullable=False)

    platform_fee = Column(Float, default=0.0)
    traveler_fee = Column(Float, default=0.0)
    total_charged = Column(Float, default=0.0)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buyer_orders")
    traveler = relationship("User", foreign_keys=[traveler_id], back_populates="traveler_orders")
    trip = relationship("Trip", back_populates="orders")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")


# ---------------------------------------------------------
# ORDER EVENT MODEL
# ---------------------------------------------------------
class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="events")





    





