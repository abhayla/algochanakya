import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for storing user account information."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(100), nullable=True)
    email = Column(
        String, unique=True, nullable=True, index=True
    )  # Can be null for broker-only users
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    # User preferences
    user_preferences = relationship(
        "UserPreferences", back_populates="user", uselist=False
    )

    # AutoPilot relationships
    autopilot_settings = relationship(
        "AutoPilotUserSettings", back_populates="user", uselist=False
    )
    autopilot_strategies = relationship("AutoPilotStrategy", back_populates="user")

    # AI relationships
    ai_config = relationship("AIUserConfig", back_populates="user", uselist=False)

    # SmartAPI credentials (legacy — being replaced by broker_api_credentials)
    smartapi_credentials = relationship(
        "SmartAPICredentials", back_populates="user", uselist=False
    )

    # Unified broker API credentials (one per broker per user)
    broker_api_credentials = relationship(
        "BrokerAPICredentials", back_populates="user"
    )

    # Broker Tier 3 credentials
    zerodha_credentials = relationship(
        "ZerodhaCredentials", back_populates="user", uselist=False
    )
    upstox_credentials = relationship(
        "UpstoxCredentials", back_populates="user", uselist=False
    )
    dhan_credentials = relationship(
        "DhanCredentials", back_populates="user", uselist=False
    )

    def __repr__(self):
        return f"<User {self.id} first_name={self.first_name} email={self.email}>"
