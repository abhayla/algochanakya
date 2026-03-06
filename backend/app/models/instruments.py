import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, DECIMAL, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class Instrument(Base):
    """Instrument master data (broker-agnostic)."""

    __tablename__ = "instruments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Instrument identification
    instrument_token = Column(Integer, nullable=False, index=True)
    exchange_token = Column(Integer, nullable=True)
    tradingsymbol = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=True)

    # Exchange and segment
    exchange = Column(String(10), nullable=False)  # NSE, BSE, NFO, BFO, MCX
    segment = Column(String(20), nullable=True)
    instrument_type = Column(String(20), nullable=True)  # EQ, FUT, CE, PE

    # Options/Futures specific
    option_type = Column(String(5), nullable=True)  # CE, PE (explicit option type)
    strike = Column(DECIMAL(10, 2), nullable=True)
    expiry = Column(Date, nullable=True)

    # Trading details
    lot_size = Column(Integer, default=1, nullable=False)
    tick_size = Column(DECIMAL(10, 4), default=0.05, nullable=False)

    # Broker source tracking
    source_broker = Column(String(20), nullable=False, default="kite")

    # Timestamp
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('instrument_token', 'source_broker', name='uq_instrument_token_source_broker'),
        Index('idx_instruments_tradingsymbol', 'tradingsymbol'),
        Index('idx_instruments_token', 'instrument_token'),
        Index('idx_instruments_exchange', 'exchange'),
        Index('idx_instruments_source_broker', 'source_broker'),
        Index('idx_instruments_name_exchange_type', 'name', 'exchange', 'instrument_type'),
    )

    def __repr__(self):
        return f"<Instrument {self.tradingsymbol} token={self.instrument_token} exchange={self.exchange} source={self.source_broker}>"
