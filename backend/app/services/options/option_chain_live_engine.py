"""
Option Chain Live Engine — Ticker-fed in-memory snapshot cache.

Subscribes to TickerPool for option chain tokens, maintains an in-memory
snapshot of LTP/OI/volume per token. API requests are served from memory
instead of hitting broker APIs, reducing response time from seconds to <1ms.

Architecture:
    TickerPool → composite callback → engine.on_tick() (sync, hot path)
                                    → router.dispatch() (async, fan-out)

    The engine is wired into the tick pipeline via a composite callback in
    main.py lifespan. It passively listens to ALL ticks and updates snapshots
    for registered chains. No additional TickerPool subscriptions needed —
    it piggybacks on existing WebSocket client subscriptions.

Usage:
    engine = OptionChainLiveEngine.get_instance()

    # Register a chain (on first API request / cache miss)
    engine.register_chain("NIFTY", "2026-04-24", [
        {"token": 1001, "strike": 24000, "side": "CE", "tradingsymbol": "NIFTY24000CE"},
        {"token": 2001, "strike": 24000, "side": "PE", "tradingsymbol": "NIFTY24000PE"},
    ])

    # Ticks flow automatically via composite callback
    # engine.on_tick(ticks)  — called by pipeline, not by user code

    # Serve API from memory (returns None if stale or unregistered)
    snap = engine.get_fresh_snapshot("NIFTY", "2026-04-24")

    # Cleanup when no longer needed
    engine.unregister_chain("NIFTY", "2026-04-24")
"""
import logging
import time
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# Snapshot is considered fresh if ticks arrived within this window
FRESHNESS_THRESHOLD_SECONDS = 10

# Chains not accessed for this long are auto-cleaned
IDLE_EXPIRY_SECONDS = 300  # 5 minutes


class OptionChainLiveEngine:
    """In-memory option chain snapshot maintained by ticker feed."""

    _instance: Optional["OptionChainLiveEngine"] = None

    @classmethod
    def get_instance(cls) -> "OptionChainLiveEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton — for testing only."""
        cls._instance = None

    def __init__(self):
        # Key: "NIFTY:2026-04-24" → snapshot dict
        self._snapshots: dict[str, dict] = {}
        # Reverse lookup: token → set of snapshot keys (a token may appear in multiple expiries)
        self._token_to_keys: dict[int, set[str]] = {}

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

        # If already registered, just touch and return
        if key in self._snapshots:
            self._snapshots[key]["last_accessed_at"] = time.monotonic()
            return

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
            if tok not in self._token_to_keys:
                self._token_to_keys[tok] = set()
            self._token_to_keys[tok].add(key)

        now = time.monotonic()
        self._snapshots[key] = {
            "underlying": underlying,
            "expiry": expiry,
            "tokens": token_data,
            "registered_at": now,
            "last_tick_at": 0,  # No ticks received yet
            "last_accessed_at": now,
            "tick_count": 0,
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
                keys = self._token_to_keys.get(tok)
                if keys:
                    keys.discard(key)
                    if not keys:
                        del self._token_to_keys[tok]
            logger.info("[LiveEngine] Unregistered %s:%s", underlying, expiry)

    def has_snapshot(self, underlying: str, expiry: str) -> bool:
        return self._key(underlying, expiry) in self._snapshots

    def get_snapshot(self, underlying: str, expiry: str) -> Optional[dict]:
        """Get the current in-memory snapshot. Returns None if not registered."""
        snap = self._snapshots.get(self._key(underlying, expiry))
        if snap:
            snap["last_accessed_at"] = time.monotonic()
        return snap

    def get_fresh_snapshot(
        self,
        underlying: str,
        expiry: str,
        max_age_seconds: float = FRESHNESS_THRESHOLD_SECONDS,
    ) -> Optional[dict]:
        """Get snapshot only if it has received ticks recently.

        Returns None if:
        - Not registered
        - Never received any ticks
        - Last tick is older than max_age_seconds
        """
        snap = self.get_snapshot(underlying, expiry)
        if snap is None:
            return None
        if snap["last_tick_at"] == 0:
            return None
        if time.monotonic() - snap["last_tick_at"] > max_age_seconds:
            return None
        return snap

    def on_tick(self, ticks: list) -> None:
        """Process a batch of NormalizedTick objects. Called by composite callback.

        This is the hot path — must be fast. No I/O, no allocations if possible.
        Synchronous (NOT async) — the composite callback awaits router.dispatch
        separately.
        """
        now = time.monotonic()
        for tick in ticks:
            keys = self._token_to_keys.get(tick.token)
            if not keys:
                continue
            for key in keys:
                snap = self._snapshots.get(key)
                if snap is None:
                    continue
                entry = snap["tokens"].get(tick.token)
                if entry is None:
                    continue
                entry["ltp"] = tick.ltp
                entry["oi"] = tick.oi
                entry["volume"] = tick.volume
                snap["last_tick_at"] = now
                snap["tick_count"] += 1

    def cleanup_idle(self) -> int:
        """Remove chains not accessed for IDLE_EXPIRY_SECONDS. Returns count removed."""
        now = time.monotonic()
        to_remove = []
        for key, snap in self._snapshots.items():
            if now - snap["last_accessed_at"] > IDLE_EXPIRY_SECONDS:
                to_remove.append((snap["underlying"], snap["expiry"]))

        for underlying, expiry in to_remove:
            self.unregister_chain(underlying, expiry)

        if to_remove:
            logger.info("[LiveEngine] Cleaned up %d idle chains", len(to_remove))
        return len(to_remove)

    @property
    def stats(self) -> dict:
        """Diagnostic stats for health endpoints."""
        return {
            "registered_chains": len(self._snapshots),
            "tracked_tokens": len(self._token_to_keys),
            "chains": {
                key: {
                    "tick_count": snap["tick_count"],
                    "last_tick_age_s": round(time.monotonic() - snap["last_tick_at"], 1)
                    if snap["last_tick_at"] > 0
                    else None,
                    "token_count": len(snap["tokens"]),
                }
                for key, snap in self._snapshots.items()
            },
        }
