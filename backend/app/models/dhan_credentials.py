"""
Dhan Credentials SQLAlchemy Model

Stores encrypted Dhan credentials for users (Tier 3).
Persists client_id + encrypted access_token so users don't need to
re-enter them every session. Configured via the Settings page.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class DhanCredentials(Base):
    """
    Dhan static token credentials storage (Tier 3 — per-user).

    Stores client_id + encrypted access_token for persistent Dhan authentication.
    Dhan tokens are long-lived (until manually revoked), making persistent storage valuable.
    """
    __tablename__ = "dhan_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Dhan credentials (client_id plain, access_token encrypted)
    client_id = Column(String(50), nullable=False)
    encrypted_access_token = Column(Text, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="dhan_credentials")

    def __repr__(self):
        return f"<DhanCredentials(user_id={self.user_id}, client_id={self.client_id}, is_active={self.is_active})>"
