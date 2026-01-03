"""
SmartAPI Historical Data Service

REST API for historical OHLCV candle data from AngelOne SmartAPI.
Used for charts, backtesting, and after-market OHLC fallback.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from SmartApi import SmartConnect

from app.services.smartapi_instruments import get_smartapi_instruments

logger = logging.getLogger(__name__)


class SmartAPIHistoricalError(Exception):
    """Exception raised for SmartAPI historical data errors."""
    pass


class SmartAPIHistorical:
    """
    REST API service for historical candle data.

    Uses Historical Data API (getCandleData) for:
    - Historical charts
    - Backtesting data
    - After-market OHLC fallback
    """

    # Interval mapping
    INTERVALS = {
        '1m': 'ONE_MINUTE',
        '3m': 'THREE_MINUTE',
        '5m': 'FIVE_MINUTE',
        '10m': 'TEN_MINUTE',
        '15m': 'FIFTEEN_MINUTE',
        '30m': 'THIRTY_MINUTE',
        '1h': 'ONE_HOUR',
        '1d': 'ONE_DAY',
        # Also accept SmartAPI format directly
        'ONE_MINUTE': 'ONE_MINUTE',
        'THREE_MINUTE': 'THREE_MINUTE',
        'FIVE_MINUTE': 'FIVE_MINUTE',
        'TEN_MINUTE': 'TEN_MINUTE',
        'FIFTEEN_MINUTE': 'FIFTEEN_MINUTE',
        'THIRTY_MINUTE': 'THIRTY_MINUTE',
        'ONE_HOUR': 'ONE_HOUR',
        'ONE_DAY': 'ONE_DAY',
    }

    # Limits per interval
    INTERVAL_LIMITS = {
        'ONE_MINUTE': 30,      # 30 days
        'THREE_MINUTE': 60,    # 60 days
        'FIVE_MINUTE': 100,    # 100 days
        'TEN_MINUTE': 100,     # 100 days
        'FIFTEEN_MINUTE': 200, # 200 days
        'THIRTY_MINUTE': 200,  # 200 days
        'ONE_HOUR': 400,       # 400 days
        'ONE_DAY': 2000,       # ~5.5 years
    }

    def __init__(self, api_key: str, jwt_token: str):
        """
        Initialize historical data service.

        Args:
            api_key: AngelOne API key
            jwt_token: JWT token from authentication
        """
        self.api_key = api_key
        self.jwt_token = jwt_token
        self._api: Optional[SmartConnect] = None
        self._instruments = get_smartapi_instruments()

    def _get_api(self) -> SmartConnect:
        """Get or create SmartConnect instance."""
        if self._api is None:
            self._api = SmartConnect(api_key=self.api_key)
            self._api.setAccessToken(self.jwt_token)
        return self._api

    async def get_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical OHLCV candles.

        Args:
            exchange: Exchange (NSE, NFO, etc.)
            symbol_token: SmartAPI symbol token
            interval: Candle interval (1m, 5m, 15m, 1h, 1d, etc.)
            from_date: Start date "YYYY-MM-DD HH:MM"
            to_date: End date "YYYY-MM-DD HH:MM"

        Returns:
            List of candle dicts with timestamp, open, high, low, close, volume

        Raises:
            SmartAPIHistoricalError: If fetch fails
        """
        try:
            api = self._get_api()

            # Map interval
            smartapi_interval = self.INTERVALS.get(interval.lower(), interval.upper())
            if smartapi_interval not in self.INTERVALS.values():
                raise SmartAPIHistoricalError(f"Invalid interval: {interval}")

            # Build request payload
            payload = {
                "exchange": exchange,
                "symboltoken": symbol_token,
                "interval": smartapi_interval,
                "fromdate": from_date,
                "todate": to_date
            }

            logger.info(f"[SmartAPI] Fetching {smartapi_interval} candles for {symbol_token} on {exchange}")

            # Call API
            response = api.getCandleData(payload)

            if not response or response.get('status') != True:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"[SmartAPI] Historical fetch failed: {error_msg}")
                raise SmartAPIHistoricalError(f"Historical fetch failed: {error_msg}")

            # Parse candles
            return self._parse_candles(response.get('data', []))

        except SmartAPIHistoricalError:
            raise
        except Exception as e:
            logger.error(f"[SmartAPI] Historical error: {e}")
            raise SmartAPIHistoricalError(f"Historical fetch failed: {e}")

    def _parse_candles(self, data: List[List]) -> List[Dict[str, Any]]:
        """
        Parse raw candle data from SmartAPI.

        SmartAPI returns: [[timestamp, open, high, low, close, volume], ...]

        Args:
            data: Raw candle data list

        Returns:
            List of normalized candle dicts
        """
        result = []

        for candle in data:
            if len(candle) >= 6:
                result.append({
                    'timestamp': candle[0],  # ISO format string
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': int(candle[5]),
                })

        return result

    async def get_ohlc(
        self,
        instruments: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get today's OHLC for instruments (for after-market fallback).

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings

        Returns:
            Dict mapping instrument to OHLC data
        """
        result = {}
        today = datetime.now()
        from_date = today.strftime("%Y-%m-%d 09:15")
        to_date = today.strftime("%Y-%m-%d 15:30")

        for inst in instruments:
            try:
                if ':' in inst:
                    exchange, symbol = inst.split(':', 1)
                else:
                    exchange = 'NFO'
                    symbol = inst

                # Lookup token
                token = await self._instruments.lookup_token(symbol, exchange)
                if not token:
                    logger.warning(f"[SmartAPI] Token not found for {inst}")
                    continue

                # Get daily candle
                candles = await self.get_candles(
                    exchange=exchange,
                    symbol_token=token,
                    interval='1d',
                    from_date=from_date,
                    to_date=to_date
                )

                if candles:
                    latest = candles[-1]  # Most recent candle
                    result[inst] = {
                        'open': latest['open'],
                        'high': latest['high'],
                        'low': latest['low'],
                        'close': latest['close'],
                        'volume': latest['volume'],
                        'timestamp': latest['timestamp'],
                    }

            except Exception as e:
                logger.warning(f"[SmartAPI] OHLC fetch failed for {inst}: {e}")

        return result

    async def get_intraday(
        self,
        exchange: str,
        symbol: str,
        interval: str = '5m',
        days: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get intraday candles for a symbol.

        Args:
            exchange: Exchange (NSE, NFO, etc.)
            symbol: Trading symbol
            interval: Candle interval (1m, 5m, 15m, etc.)
            days: Number of days to fetch

        Returns:
            List of candle dicts
        """
        # Lookup token
        token = await self._instruments.lookup_token(symbol, exchange)
        if not token:
            raise SmartAPIHistoricalError(f"Token not found for {exchange}:{symbol}")

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        return await self.get_candles(
            exchange=exchange,
            symbol_token=token,
            interval=interval,
            from_date=from_date.strftime("%Y-%m-%d 09:15"),
            to_date=to_date.strftime("%Y-%m-%d 15:30")
        )

    async def get_daily(
        self,
        exchange: str,
        symbol: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily candles for a symbol.

        Args:
            exchange: Exchange (NSE, NFO, etc.)
            symbol: Trading symbol
            days: Number of days to fetch

        Returns:
            List of daily candle dicts
        """
        # Lookup token
        token = await self._instruments.lookup_token(symbol, exchange)
        if not token:
            raise SmartAPIHistoricalError(f"Token not found for {exchange}:{symbol}")

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        return await self.get_candles(
            exchange=exchange,
            symbol_token=token,
            interval='1d',
            from_date=from_date.strftime("%Y-%m-%d 09:15"),
            to_date=to_date.strftime("%Y-%m-%d 15:30")
        )

    async def get_index_historical(
        self,
        index: str,
        interval: str = '1d',
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical data for an index.

        Args:
            index: Index name (NIFTY, BANKNIFTY, etc.)
            interval: Candle interval
            days: Number of days to fetch

        Returns:
            List of candle dicts
        """
        # Index tokens in SmartAPI
        index_tokens = {
            'NIFTY': {'exchange': 'NSE', 'token': '99926000'},
            'BANKNIFTY': {'exchange': 'NSE', 'token': '99926009'},
            'FINNIFTY': {'exchange': 'NSE', 'token': '99926037'},
            'SENSEX': {'exchange': 'BSE', 'token': '99919000'},
        }

        index_info = index_tokens.get(index.upper())
        if not index_info:
            raise SmartAPIHistoricalError(f"Unknown index: {index}")

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        return await self.get_candles(
            exchange=index_info['exchange'],
            symbol_token=index_info['token'],
            interval=interval,
            from_date=from_date.strftime("%Y-%m-%d 09:15"),
            to_date=to_date.strftime("%Y-%m-%d 15:30")
        )


def create_historical_service(
    api_key: str,
    jwt_token: str
) -> SmartAPIHistorical:
    """
    Create a new SmartAPIHistorical instance.

    Args:
        api_key: AngelOne API key (use ANGEL_API_KEY_HISTORICAL)
        jwt_token: JWT token from authentication

    Returns:
        SmartAPIHistorical instance
    """
    return SmartAPIHistorical(api_key, jwt_token)


def get_historical_api_key() -> str:
    """Get the API key for historical data."""
    from app.config import settings
    return settings.ANGEL_API_KEY_HISTORICAL or settings.ANGEL_API_KEY
