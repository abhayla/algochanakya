"""
SmartAPI Credentials SQLAlchemy Model

Stores encrypted AngelOne SmartAPI credentials for users.
Credentials are encrypted using Fernet symmetric encryption.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SmartAPICredentials(Base):
    """
    SmartAPI credentials storage.

    Stores encrypted credentials for AngelOne SmartAPI authentication.
    - client_id: AngelOne trading account ID (not encrypted, used as identifier)
    - encrypted_pin: Fernet-encrypted trading PIN
    - encrypted_totp_secret: Fernet-encrypted TOTP secret for auto-generation
    - jwt_token: Current session JWT token (refreshed on auth)
    - feed_token: Current feed token for WebSocket (refreshed on auth)
    """
    __tablename__ = "smartapi_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # AngelOne credentials (client_id stored plain, others encrypted)
    client_id = Column(String(20), nullable=False)
    encrypted_pin = Column(Text, nullable=False)
    encrypted_totp_secret = Column(Text, nullable=False)

    # Session tokens (stored for reuse until expiry)
    jwt_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    feed_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="smartapi_credentials")

    def __repr__(self):
        return f"<SmartAPICredentials(user_id={self.user_id}, client_id={self.client_id}, is_active={self.is_active})>"
