"""
Broker Instrument Token Mapping

Maps canonical symbols (Kite format) to broker-specific symbols and tokens.
Populated daily via scheduled job that downloads instruments from each broker.

Example mappings:
┌───────────────────────────┬─────────┬───────────────────────────┬──────────────┐
│ canonical_symbol          │ broker  │ broker_symbol             │ broker_token │
├───────────────────────────┼─────────┼───────────────────────────┼──────────────┤
│ NIFTY25APR25000CE         │ kite    │ NIFTY25APR25000CE         │ 13123586     │
│ NIFTY25APR25000CE         │ smartapi│ NIFTY24APR2525000CE       │ 49159        │
│ NIFTY25APR25000CE         │ upstox  │ NIFTY 25000 CE 24 APR 25  │ 150429       │
└───────────────────────────┴─────────┴───────────────────────────┴──────────────┘
"""

from sqlalchemy import Column, String, BigInteger, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.database import Base


class BrokerInstrumentToken(Base):
    """Maps canonical symbols to broker-specific symbols and tokens."""
    __tablename__ = "broker_instrument_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Canonical symbol (Kite format - our internal standard)
    canonical_symbol = Column(String(50), nullable=False, index=True)

    # Broker identification
    broker = Column(String(20), nullable=False, index=True)  # smartapi, kite, upstox, dhan, fyers, paytm

    # Broker-specific data
    broker_symbol = Column(String(100), nullable=False)
    broker_token = Column(BigInteger, nullable=False)

    # Instrument details
    exchange = Column(String(10), nullable=False)  # NSE, NFO, BSE, BFO, MCX
    underlying = Column(String(20), nullable=True)  # NIFTY, BANKNIFTY, etc.
    expiry = Column(Date, nullable=True)  # For cleanup of expired contracts

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Unique constraint: one mapping per symbol per broker
        UniqueConstraint('canonical_symbol', 'broker', name='uq_symbol_broker'),

        # Indexes for fast lookups
        Index('idx_broker_token', 'broker', 'broker_token'),
        Index('idx_canonical_symbol', 'canonical_symbol'),
        Index('idx_broker_symbol', 'broker', 'broker_symbol'),
        Index('idx_expiry', 'expiry'),  # For cleanup of expired contracts
    )

    def __repr__(self):
        return f"<BrokerInstrumentToken({self.canonical_symbol} -> {self.broker}:{self.broker_symbol})>"
