"""
EOD Option Chain Snapshot model.

Stores end-of-day option chain data (OI, LTP, Volume, IV) per strike
fetched from NSE v3 API. Used as fallback when brokers return zeros
outside market hours.
"""
import uuid
from sqlalchemy import (
    Column, String, Date, DateTime, BigInteger, Index, UniqueConstraint,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from app.database import Base


class EODOptionSnapshot(Base):
    __tablename__ = "eod_option_snapshots"

    id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    underlying = Column(String(20), nullable=False)
    expiry_date = Column(Date, nullable=False)
    strike = Column(DECIMAL(10, 2), nullable=False)

    ce_ltp = Column(DECIMAL(12, 2), default=0)
    ce_oi = Column(BigInteger, default=0)
    ce_volume = Column(BigInteger, default=0)
    ce_iv = Column(DECIMAL(8, 2), default=0)

    pe_ltp = Column(DECIMAL(12, 2), default=0)
    pe_oi = Column(BigInteger, default=0)
    pe_volume = Column(BigInteger, default=0)
    pe_iv = Column(DECIMAL(8, 2), default=0)

    spot_price = Column(DECIMAL(12, 2), nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "underlying", "expiry_date", "strike",
            name="uq_eod_snapshot_strike",
        ),
        Index("idx_eod_snapshot_lookup", "underlying", "expiry_date"),
    )

    def __repr__(self):
        return (
            f"<EODOptionSnapshot {self.underlying} {self.expiry_date} "
            f"strike={self.strike}>"
        )
