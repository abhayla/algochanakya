"""
Deprecated services — kept for reference only.

These modules were replaced by the Phase T4 multi-broker ticker architecture:
  - smartapi_ticker.py → app.services.brokers.market_data.ticker.adapters.smartapi
  - kite_ticker.py     → app.services.brokers.market_data.ticker.adapters.kite

DO NOT import from this package in new code.
"""
