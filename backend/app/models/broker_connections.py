import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class BrokerConnection(Base):
    """Broker connection model for storing user's broker authentication."""

    __tablename__ = "broker_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Broker information
    broker = Column(String(50), nullable=False)  # "zerodha", "angelone", "upstox"
    broker_user_id = Column(String(100), nullable=False)  # Broker's client ID (e.g., "AB1234")

    # Tokens (encrypted in production)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)  # Not all brokers provide refresh tokens
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Broker-specific metadata (e.g., Paytm's extra tokens, Fyers client_id)
    broker_metadata = Column(JSONB, nullable=True, default=dict)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<BrokerConnection user_id={self.user_id} broker={self.broker} active={self.is_active}>"
