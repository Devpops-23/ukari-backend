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
# USER MODEL (buyers + travelers + admins)
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Basic identity
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)

    # Role: buyer, traveler, admin
    role = Column(String, default="buyer")

    # Auth token (optional)
    access_token = Column(String, nullable=True, index=True)

    # Contact
    phone = Column(String, nullable=True)

    # Stripe
    stripe_account_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    default_payment_method = Column(String, nullable=True)
    account_verified = Column(Boolean, default=False)

    # Traveler shipping address
    shipping_address_line1 = Column(String, nullable=True)
    shipping_address_line2 = Column(String, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_state = Column(String, nullable=True)
    shipping_postal_code = Column(String, nullable=True)
    shipping_country = Column(String, nullable=True)

    # Performance
    rating = Column(Float, default=0.0)
    reliability_score = Column(Float, default=100.0)
    on_time_deliveries = Column(Integer, default=0)
    late_deliveries = Column(Integer, default=0)
    cancellation_count = Column(Integer, default=0)
    flight_cancel_count = Column(Integer, default=0)

    # Buyer fraud counters
    chargeback_count = Column(Integer, default=0)
    return_count = Column(Integer, default=0)

    # Account status
    status = Column(String, default="active")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trips = relationship("Trip", back_populates="traveler", cascade="all, delete-orphan")
    traveler_orders = relationship("Order", foreign_keys="Order.traveler_id", back_populates="traveler")
    buyer_orders = relationship("Order", foreign_keys="Order.buyer_id", back_populates="buyer")


# ---------------------------------------------------------
# ORDER MODEL
# ---------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Marketplace product details
    product_source = Column(String, nullable=True)
    product_url = Column(Text, nullable=True)
    product_sku = Column(String, nullable=True)
    store_name = Column(String, nullable=True)
    item_name = Column(String, nullable=True)

    # Pricing breakdown
    item_price = Column(Float, nullable=True)
    platform_fee = Column(Float, nullable=True)
    traveler_fee = Column(Float, nullable=True)
    total_charged = Column(Float, nullable=True)

    # Purchase lifecycle
    purchase_status = Column(String, default="pending")
    purchase_reference = Column(String, nullable=True)

    # Shipment to traveler
    shipment_status = Column(String, default="not_shipped")
    shipment_tracking_number = Column(String, nullable=True)
    shipment_carrier = Column(String, nullable=True)
    traveler_received_at = Column(DateTime, nullable=True)

    # Delivery to final recipient
    pickup_location = Column(String, nullable=True)
    delivery_location = Column(String, nullable=True)

    # High-level status
    status = Column(String, default="pending")

    # Delivery proof
    proof_photo_filename = Column(String, nullable=True)

    # Dispute fields
    dispute_reason = Column(Text, nullable=True)
    dispute_status = Column(String, nullable=True)
    dispute_created_at = Column(DateTime, nullable=True)

    # Stripe payout tracking
    stripe_transfer_id = Column(String, nullable=True)

    # Earnings
    amount_earned = Column(Float, default=0.0)

    # Enforcement
    traveler_arrived_at = Column(DateTime, nullable=True)
    delivery_deadline = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    auto_charge_executed = Column(Boolean, default=False)

    # Additional lifecycle timestamps
    flight_cancelled_at = Column(DateTime, nullable=True)
    returned_to_store_at = Column(DateTime, nullable=True)
    rerouted_at = Column(DateTime, nullable=True)

    # Fraud flag
    flagged = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    buyer_confirmed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    trip = relationship("Trip", back_populates="orders")
    traveler = relationship("User", foreign_keys=[traveler_id], back_populates="traveler_orders")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buyer_orders")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")


# ---------------------------------------------------------
# ORDER EVENT MODEL
# ---------------------------------------------------------
class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="events")


# ---------------------------------------------------------
# TRIP MODEL
# ---------------------------------------------------------
class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    max_weight = Column(Float, nullable=True)

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    travel_date = Column(DateTime, nullable=False)

    status = Column(String, default="active")

    total_earned = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="trip")
    traveler = relationship("User", back_populates="trips")

    





