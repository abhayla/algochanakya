"""
Zerodha Credentials SQLAlchemy Model

Stores encrypted Zerodha Kite Connect app credentials for users (Tier 3).
These are the user's OWN Kite Connect app api_key + api_secret, not the
platform's. Configured via the Settings page.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ZerodhaCredentials(Base):
    """
    Zerodha Kite Connect app credentials storage (Tier 3 — per-user).

    Stores api_key + encrypted api_secret for the user's own Kite Connect app.
    Enables OAuth login using the user's own app instead of the platform's.
    """
    __tablename__ = "zerodha_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Kite Connect app credentials (api_key plain, api_secret encrypted)
    api_key = Column(String(64), nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="zerodha_credentials")

    def __repr__(self):
        return f"<ZerodhaCredentials(user_id={self.user_id}, api_key={self.api_key[:8]}..., is_active={self.is_active})>"
