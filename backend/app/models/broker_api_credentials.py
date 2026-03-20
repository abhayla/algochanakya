"""
Broker API Credentials SQLAlchemy Model

Unified table storing market data API credentials for ALL brokers (Tier 3).
Replaces per-broker tables (smartapi_credentials, zerodha_credentials,
upstox_credentials, dhan_credentials) with a single table.

These are the user's own API credentials configured via the Settings page,
used for market data (live prices, WebSocket). Completely separate from
login tokens stored in broker_connections (used for order execution).
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class BrokerAPICredentials(Base):
    """
    Unified broker API credentials for market data (Tier 3).

    One row per user per broker. Stores permanent API credentials
    (api_key, api_secret) and session tokens (access_token, feed_token)
    for market data access.

    IMPORTANT: This table is for MARKET DATA only.
    Order execution tokens live in broker_connections.
    """
    __tablename__ = "broker_api_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "broker", name="uq_broker_api_credentials_user_broker"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Broker identifier: "angelone", "zerodha", "upstox", "dhan", "fyers", "paytm"
    broker = Column(String(50), nullable=False, index=True)

    # Permanent API credentials (encrypted)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)

    # Broker-specific auth fields (encrypted, nullable — only some brokers need these)
    client_id = Column(String(100), nullable=True)
    encrypted_pin = Column(Text, nullable=True)
    encrypted_totp_secret = Column(Text, nullable=True)

    # Session tokens (refreshed on auth)
    access_token = Column(Text, nullable=True)
    feed_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=False, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Broker-specific extras (e.g., Paytm's public_access_token, read_access_token)
    broker_metadata = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="broker_api_credentials")

    def __repr__(self):
        return f"<BrokerAPICredentials(user_id={self.user_id}, broker={self.broker}, is_active={self.is_active})>"
