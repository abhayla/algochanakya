"""
Option Chain Live Engine — Ticker-fed in-memory snapshot cache.

Subscribes to TickerPool for option chain tokens, maintains an in-memory
snapshot of LTP/OI/volume per token. API requests are served from memory
instead of hitting broker APIs, reducing response time from seconds to <1ms.

Usage:
    engine = OptionChainLiveEngine()

    # Register a chain (typically on first API request or page load)
    engine.register_chain("NIFTY", "2026-04-24", [
        {"token": 1001, "strike": 24000, "side": "CE", "tradingsymbol": "NIFTY24000CE"},
        {"token": 2001, "strike": 24000, "side": "PE", "tradingsymbol": "NIFTY24000PE"},
    ])

    # Called by TickerPool callback on each tick batch
    engine.on_tick(ticks)  # List[NormalizedTick]

    # Serve API from memory
    snap = engine.get_snapshot("NIFTY", "2026-04-24")
    # snap["tokens"][1001]["ltp"] → Decimal("250.50")

    # Cleanup when no longer needed
    engine.unregister_chain("NIFTY", "2026-04-24")
"""
import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class OptionChainLiveEngine:
    """In-memory option chain snapshot maintained by ticker feed."""

    def __init__(self):
        # Key: "NIFTY:2026-04-24" → snapshot dict
        self._snapshots: dict[str, dict] = {}
        # Reverse lookup: token → snapshot key (for fast tick routing)
        self._token_to_key: dict[int, str] = {}

    @staticmethod
    def _key(underlying: str, expiry: str) -> str:
        return f"{underlying}:{expiry}"

    def register_chain(self, underlying: str, expiry: str, tokens: list[dict]) -> None:
        """Register a chain for live tracking.

        Args:
            underlying: e.g., "NIFTY"
            expiry: e.g., "2026-04-24"
            tokens: List of dicts with keys: token, strike, side, tradingsymbol
        """
        key = self._key(underlying, expiry)

        token_data = {}
        for t in tokens:
            tok = t["token"]
            token_data[tok] = {
                "ltp": Decimal("0"),
                "oi": 0,
                "volume": 0,
                "strike": t["strike"],
                "side": t["side"],
                "tradingsymbol": t["tradingsymbol"],
            }
            self._token_to_key[tok] = key

        self._snapshots[key] = {
            "underlying": underlying,
            "expiry": expiry,
            "tokens": token_data,
        }

        logger.info(
            "[LiveEngine] Registered %s:%s with %d tokens",
            underlying, expiry, len(tokens)
        )

    def unregister_chain(self, underlying: str, expiry: str) -> None:
        """Remove a chain from live tracking."""
        key = self._key(underlying, expiry)
        snap = self._snapshots.pop(key, None)
        if snap:
            for tok in snap["tokens"]:
                self._token_to_key.pop(tok, None)
            logger.info("[LiveEngine] Unregistered %s:%s", underlying, expiry)

    def has_snapshot(self, underlying: str, expiry: str) -> bool:
        return self._key(underlying, expiry) in self._snapshots

    def get_snapshot(self, underlying: str, expiry: str) -> Optional[dict]:
        """Get the current in-memory snapshot. Returns None if not registered."""
        return self._snapshots.get(self._key(underlying, expiry))

    def on_tick(self, ticks: list) -> None:
        """Process a batch of NormalizedTick objects. Called by TickerPool callback.

        This is the hot path — must be fast. No I/O, no allocations if possible.
        """
        for tick in ticks:
            key = self._token_to_key.get(tick.token)
            if key is None:
                continue
            snap = self._snapshots.get(key)
            if snap is None:
                continue
            entry = snap["tokens"].get(tick.token)
            if entry is None:
                continue

            entry["ltp"] = tick.ltp
            entry["oi"] = tick.oi
            entry["volume"] = tick.volume
