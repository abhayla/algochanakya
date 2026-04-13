"""
Multi-broker ticker system — 5-component architecture.

Components:
- NormalizedTick: Universal tick data model (Decimal prices, canonical tokens)
- TickerAdapter: Abstract base for broker WebSocket adapters
- TickerPool: Adapter lifecycle + ref-counted subscriptions (singleton)
- TickerRouter: User WebSocket fan-out + tick dispatch (singleton)
- HealthMonitor: Per-broker health scoring (5s heartbeat)
- FailoverController: Make-before-break switching + failback
- token_policy: Auth error classification + retry categories

Usage:
    from app.services.brokers.market_data.ticker import (
        NormalizedTick, TickerAdapter, TickerPool, TickerRouter,
        HealthMonitor, FailoverController,
    )

    # SmartAPI adapter
    from app.services.brokers.market_data.ticker.adapters import SmartAPITickerAdapter
"""

from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.pool import TickerPool
from app.services.brokers.market_data.ticker.router import TickerRouter
from app.services.brokers.market_data.ticker.health import HealthMonitor
from app.services.brokers.market_data.ticker.failover import FailoverController
from app.services.brokers.market_data.ticker.adapters.smartapi import SmartAPITickerAdapter
from app.services.brokers.market_data.ticker.adapters.kite import KiteTickerAdapter
from app.services.brokers.market_data.ticker.adapters.dhan import DhanTickerAdapter
from app.services.brokers.market_data.ticker.adapters.fyers import FyersTickerAdapter
from app.services.brokers.market_data.ticker.adapters.upstox import UpstoxTickerAdapter
from app.services.brokers.market_data.ticker.adapters.paytm import PaytmTickerAdapter

__all__ = [
    "NormalizedTick",
    "TickerAdapter",
    "TickerPool",
    "TickerRouter",
    "HealthMonitor",
    "FailoverController",
    "SmartAPITickerAdapter",
    "KiteTickerAdapter",
    "DhanTickerAdapter",
    "FyersTickerAdapter",
    "UpstoxTickerAdapter",
    "PaytmTickerAdapter",
]
