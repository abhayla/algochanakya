"""
NormalizedTick — Universal tick data model for all broker adapters.

All broker WebSocket adapters convert their native tick format into NormalizedTick
before dispatching. This ensures consumers (TickerRouter, WebSocket route, etc.)
never deal with broker-specific quirks.

Key invariants:
- All prices in RUPEES (Decimal), never paise
- Token is canonical Kite instrument_token (int)
- Timestamps in IST
- broker_type identifies the source adapter
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any


@dataclass(slots=True)
class NormalizedTick:
    """
    Broker-agnostic tick from a WebSocket adapter.

    Adapters must:
    - Convert paise → rupees (SmartAPI, Kite)
    - Map broker tokens → canonical Kite tokens
    - Set broker_type to their identifier
    """

    # Primary identifier — canonical Kite instrument token
    token: int

    # Prices in RUPEES (Decimal for financial precision)
    ltp: Decimal
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    close: Decimal = Decimal("0")

    # Change metrics
    change: Decimal = Decimal("0")
    change_percent: Decimal = Decimal("0")

    # Volume & OI
    volume: int = 0
    oi: int = 0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    broker_type: str = ""

    # Optional depth fields
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict (Decimal → float for WebSocket transmission)."""
        d: Dict[str, Any] = {
            "token": self.token,
            "ltp": float(self.ltp),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "change": float(self.change),
            "change_percent": float(self.change_percent),
            "volume": self.volume,
            "oi": self.oi,
            "timestamp": self.timestamp.isoformat(),
            "broker_type": self.broker_type,
        }
        if self.bid is not None:
            d["bid"] = float(self.bid)
        if self.ask is not None:
            d["ask"] = float(self.ask)
        if self.bid_qty is not None:
            d["bid_qty"] = self.bid_qty
        if self.ask_qty is not None:
            d["ask_qty"] = self.ask_qty
        return d
