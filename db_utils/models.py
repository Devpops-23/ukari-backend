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
    password_hash = Column(String, nullable=False)

    # Role: buyer, traveler, admin
    role = Column(String, default="buyer")

    # Auth token (optional)
    access_token = Column(String, nullable=True, index=True)

    # Stripe Connect account ID (for traveler payouts)
    stripe_account_id = Column(String, nullable=True)

    # Traveler shipping address (for marketplace shipments)
    shipping_address_line1 = Column(String, nullable=True)
    shipping_address_line2 = Column(String, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_state = Column(String, nullable=True)
    shipping_postal_code = Column(String, nullable=True)
    shipping_country = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trips = relationship("Trip", back_populates="traveler", cascade="all, delete-orphan")
    traveler_orders = relationship(
        "Order",
        foreign_keys="Order.traveler_id",
        back_populates="traveler",
    )
    buyer_orders = relationship(
        "Order",
        foreign_keys="Order.buyer_id",
        back_populates="buyer",
    )

# Order model
flagged = Column(Boolean, default=False)

# User model
cancellation_count = Column(Integer, default=0)
flight_cancel_count = Column(Integer, default=0)

# Buyer fraud counters
chargeback_count = Column(Integer, default=0)
return_count = Column(Integer, default=0)

# Account status
status = Column(String, default="active")  # active, suspended, banned

# ---------------------------------------------------------
# ORDER MODEL (EXTENDED FOR MARKETPLACE + SHIPMENT FLOW)
# ---------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Traveler accepts order
    accepted_at = Column(DateTime, nullable=True)

    # Relationships
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # -----------------------------
    # Marketplace product details
    # -----------------------------
    product_source = Column(String, nullable=True)  # amazon, walmart, macys, costco
    product_url = Column(Text, nullable=True)
    product_sku = Column(String, nullable=True)

    # Pricing breakdown
    item_price = Column(Float, nullable=True)
    platform_fee = Column(Float, nullable=True)
    traveler_fee = Column(Float, nullable=True)
    total_charged = Column(Float, nullable=True)

    # -----------------------------
    # Purchase lifecycle
    # -----------------------------
    purchase_status = Column(String, default="pending")  # pending, purchased, failed
    purchase_reference = Column(String, nullable=True)   # Amazon/Walmart order ID

    # -----------------------------
    # Shipment to traveler
    # -----------------------------
    shipment_status = Column(String, default="not_shipped")  # not_shipped, in_transit, delivered_to_traveler
    shipment_tracking_number = Column(String, nullable=True)
    shipment_carrier = Column(String, nullable=True)
    traveler_received_at = Column(DateTime, nullable=True)

    status = Column(String, default="pending")  
    # Add these new statuses:
    # flight_cancelled, returned_to_store, refund_received, reordered, rerouted

    # -----------------------------
    # Delivery to final recipient
    # -----------------------------
    amount = Column(Float, nullable=False)
    store_name = Column(String, nullable=True)
    item_name = Column(String, nullable=True)
    pickup_location = Column(String, nullable=True)
    delivery_location = Column(String, nullable=True)

    # Status lifecycle:
    # pending → accepted → delivered → buyer_confirmed → paid
    # disputed (can occur after delivered)
    status = Column(String, default="pending")

    # Delivery proof
    proof_photo_filename = Column(String, nullable=True)

    # Dispute fields
    dispute_reason = Column(Text, nullable=True)
    dispute_status = Column(String, default=None)  # open, resolved, rejected
    dispute_created_at = Column(DateTime, nullable=True)

    # Stripe payout tracking
    stripe_transfer_id = Column(String, nullable=True)

    # Earnings (for traveler)
    amount_earned = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    buyer_confirmed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    trip = relationship("Trip", back_populates="orders")
    traveler = relationship("User", foreign_keys=[traveler_id], back_populates="traveler_orders")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buyer_orders")

class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    event_type = Column(String, nullable=False)  # e.g. "purchase_completed", "payout_released"
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", backref="events")
    traveler_arrived_at = Column(DateTime, nullable=True)
    delivery_deadline = Column(DateTime, nullable=True)

# Order model
flagged = Column(Boolean, default=False)

# User model
cancellation_count = Column(Integer, default=0)
flight_cancel_count = Column(Integer, default=0)

# ---------------------------------------------------------
# TRIP MODEL
# ---------------------------------------------------------
class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    # Traveler who owns this trip
    traveler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    max_weight = Column(Float, nullable=True)

    # Trip details
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    travel_date = Column(DateTime, nullable=False)

    # Status lifecycle:
    # active → completed → cancelled
    status = Column(String, default="active")

    # Earnings summary
    total_earned = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="trip")
    traveler = relationship("User", back_populates="trips")




