"""
Market Data Service

Fetches real-time market data from Kite Connect API.
Provides LTP, OHLC, VIX, and spot prices.
"""
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging

from kiteconnect import KiteConnect

from app.config import settings
from app.constants import INDEX_TOKENS, INDEX_EXCHANGES, get_index_symbol

logger = logging.getLogger(__name__)


@dataclass
class MarketQuote:
    """Market quote data."""
    instrument_token: int
    tradingsymbol: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: int
    timestamp: datetime


@dataclass
class SpotData:
    """Spot/Index data."""
    symbol: str
    ltp: Decimal
    change: Decimal
    change_pct: float
    timestamp: datetime


class MarketDataService:
    """Service for fetching market data from Kite Connect."""

    def __init__(self, kite: KiteConnect):
        self.kite = kite
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = 1  # seconds

    async def get_ltp(self, instruments: List[str]) -> Dict[str, Decimal]:
        """
        Get Last Traded Price for instruments.

        Args:
            instruments: List of instrument identifiers (e.g., ["NFO:NIFTY24DEC24500CE"])

        Returns:
            Dict mapping instrument to LTP
        """
        try:
            # Kite API call (sync, wrap in executor)
            loop = asyncio.get_event_loop()
            ltp_data = await loop.run_in_executor(
                None,
                self.kite.ltp,
                instruments
            )

            result = {}
            for key, data in ltp_data.items():
                result[key] = Decimal(str(data['last_price']))

            return result
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            raise

    async def get_quote(self, instruments: List[str]) -> Dict[str, MarketQuote]:
        """
        Get full quote for instruments.

        Args:
            instruments: List of instrument identifiers

        Returns:
            Dict mapping instrument to MarketQuote
        """
        try:
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                instruments
            )

            result = {}
            for key, data in quote_data.items():
                ohlc = data.get('ohlc', {})
                result[key] = MarketQuote(
                    instrument_token=data['instrument_token'],
                    tradingsymbol=data.get('tradingsymbol', key),
                    ltp=Decimal(str(data['last_price'])),
                    open=Decimal(str(ohlc.get('open', 0))),
                    high=Decimal(str(ohlc.get('high', 0))),
                    low=Decimal(str(ohlc.get('low', 0))),
                    close=Decimal(str(ohlc.get('close', 0))),
                    volume=data.get('volume', 0),
                    oi=data.get('oi', 0),
                    timestamp=datetime.now()
                )

            return result
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            raise

    async def get_spot_price(self, underlying: str) -> SpotData:
        """
        Get spot price for an underlying index.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY, SENSEX

        Returns:
            SpotData with current price and change
        """
        underlying_upper = underlying.upper()
        token = INDEX_TOKENS.get(underlying_upper)
        if not token:
            raise ValueError(f"Unknown underlying: {underlying}")

        # Check cache
        cache_key = f"spot_{underlying_upper}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            # Get trading symbol from centralized constants
            instrument = get_index_symbol(underlying_upper)
            if not instrument:
                exchange = INDEX_EXCHANGES.get(underlying_upper, "NSE")
                instrument = f"{exchange}:{underlying_upper}"

            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                [instrument]
            )

            data = quote_data[instrument]
            ohlc = data.get('ohlc', {})
            close = float(ohlc.get('close', 0))
            ltp = float(data['last_price'])

            # Calculate change
            change = ltp - close if close > 0 else 0
            change_pct = (change / close * 100) if close > 0 else 0

            spot = SpotData(
                symbol=underlying_upper,
                ltp=Decimal(str(data['last_price'])),
                change=Decimal(str(change)),
                change_pct=change_pct,
                timestamp=datetime.now()
            )

            # Cache result
            self._cache[cache_key] = spot
            self._cache_expiry[cache_key] = datetime.now()

            return spot
        except Exception as e:
            logger.error(f"Error fetching spot price for {underlying}: {e}")
            raise

    async def get_vix(self) -> Decimal:
        """
        Get current India VIX value.

        Returns:
            VIX value as Decimal
        """
        cache_key = "vix"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                ["NSE:INDIA VIX"]
            )

            vix = Decimal(str(quote_data["NSE:INDIA VIX"]['last_price']))

            # Cache result
            self._cache[cache_key] = vix
            self._cache_expiry[cache_key] = datetime.now()

            return vix
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
            raise

    async def get_option_chain_ltp(
        self,
        underlying: str,
        expiry: date,
        strikes: List[Decimal]
    ) -> Dict[str, Decimal]:
        """
        Get LTP for multiple strikes in option chain.

        Args:
            underlying: NIFTY, BANKNIFTY, etc.
            expiry: Expiry date
            strikes: List of strike prices

        Returns:
            Dict mapping tradingsymbol to LTP
        """
        instruments = []
        expiry_str = expiry.strftime("%y%b%d").upper()  # e.g., "24DEC26"

        for strike in strikes:
            strike_int = int(strike)
            ce_symbol = f"NFO:{underlying}{expiry_str}{strike_int}CE"
            pe_symbol = f"NFO:{underlying}{expiry_str}{strike_int}PE"
            instruments.extend([ce_symbol, pe_symbol])

        return await self.get_ltp(instruments)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache or key not in self._cache_expiry:
            return False

        elapsed = (datetime.now() - self._cache_expiry[key]).total_seconds()
        return elapsed < self._cache_ttl

    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_expiry.clear()


# Service instance cache (per access token)
_market_data_services: Dict[str, MarketDataService] = {}


def get_market_data_service(kite: KiteConnect) -> MarketDataService:
    """Get or create MarketDataService instance for a Kite client."""
    # Use access token as key for caching
    token_key = kite.access_token or "default"

    if token_key not in _market_data_services:
        _market_data_services[token_key] = MarketDataService(kite)

    return _market_data_services[token_key]


def clear_market_data_services():
    """Clear all cached service instances."""
    global _market_data_services
    _market_data_services.clear()
