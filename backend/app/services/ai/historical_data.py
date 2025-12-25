"""
Historical Data Service

Fetches historical OHLC data from Kite Connect API with Redis caching.
Supports multiple timeframes for technical analysis and regime classification.
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
from decimal import Decimal

from kiteconnect import KiteConnect
import redis.asyncio as redis

from app.config import settings
from app.constants.trading import get_index_token, get_index_symbol

logger = logging.getLogger(__name__)


@dataclass
class OHLC:
    """OHLC candlestick data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'OHLC':
        """Create from dict (for Redis deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume']
        )


class HistoricalDataService:
    """
    Service for fetching historical OHLC data from Kite Connect API.

    Caching Strategy:
    - Intraday data (5min, 15min): 1 minute TTL
    - Daily data: 1 hour TTL
    - Cache stored in Redis for multi-user access
    """

    # Kite interval mapping
    INTERVAL_MAP = {
        "1minute": "minute",
        "3minute": "3minute",
        "5minute": "5minute",
        "10minute": "10minute",
        "15minute": "15minute",
        "30minute": "30minute",
        "60minute": "60minute",
        "day": "day"
    }

    # Cache TTL by interval type
    CACHE_TTL = {
        "minute": 60,      # 1 min for 1-minute candles
        "3minute": 60,     # 1 min
        "5minute": 60,     # 1 min
        "10minute": 60,    # 1 min
        "15minute": 60,    # 1 min
        "30minute": 120,   # 2 min
        "60minute": 300,   # 5 min
        "day": 3600        # 1 hour
    }

    def __init__(self, kite: KiteConnect, redis_client: Optional[redis.Redis] = None):
        """
        Initialize Historical Data Service.

        Args:
            kite: KiteConnect instance
            redis_client: Optional Redis client for caching
        """
        self.kite = kite
        self.redis = redis_client
        self._memory_cache: dict = {}  # Fallback if Redis unavailable

    async def get_ohlc(
        self,
        underlying: str,
        interval: str,
        from_date: date,
        to_date: date
    ) -> List[OHLC]:
        """
        Get historical OHLC data for date range.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)
            interval: Candle interval (5minute, 15minute, 60minute, day)
            from_date: Start date
            to_date: End date

        Returns:
            List of OHLC candles (oldest first)

        Raises:
            ValueError: If invalid interval or underlying
        """
        if interval not in self.INTERVAL_MAP:
            raise ValueError(f"Invalid interval: {interval}. Must be one of {list(self.INTERVAL_MAP.keys())}")

        # Get index token
        try:
            token = get_index_token(underlying)
        except KeyError:
            raise ValueError(f"Invalid underlying: {underlying}")

        # Check cache first
        cache_key = f"ohlc:{underlying}:{interval}:{from_date}:{to_date}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            logger.info(f"Cache hit for {cache_key}")
            return [OHLC.from_dict(item) for item in cached_data]

        # Fetch from Kite API
        try:
            logger.info(f"Fetching OHLC data: {underlying} {interval} from {from_date} to {to_date}")

            loop = asyncio.get_event_loop()
            kite_interval = self.INTERVAL_MAP[interval]

            historical_data = await loop.run_in_executor(
                None,
                self.kite.historical_data,
                token,
                from_date,
                to_date,
                kite_interval
            )

            # Convert to OHLC objects
            ohlc_list = []
            for candle in historical_data:
                ohlc_list.append(OHLC(
                    timestamp=candle['date'],
                    open=float(candle['open']),
                    high=float(candle['high']),
                    low=float(candle['low']),
                    close=float(candle['close']),
                    volume=candle.get('volume', 0)
                ))

            # Cache the result
            await self._save_to_cache(
                cache_key,
                [ohlc.to_dict() for ohlc in ohlc_list],
                self.CACHE_TTL.get(kite_interval, 60)
            )

            logger.info(f"Fetched {len(ohlc_list)} candles for {underlying}")
            return ohlc_list

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise

    async def get_daily_candles(self, underlying: str, days: int = 50) -> List[OHLC]:
        """
        Get daily candles for the last N days.

        Args:
            underlying: Index name
            days: Number of days to fetch (default: 50)

        Returns:
            List of daily OHLC candles
        """
        to_date = date.today()
        from_date = to_date - timedelta(days=days * 2)  # Fetch extra to account for weekends/holidays

        candles = await self.get_ohlc(underlying, "day", from_date, to_date)

        # Return only the requested number
        return candles[-days:] if len(candles) > days else candles

    async def get_intraday_candles(
        self,
        underlying: str,
        interval: str = "5minute"
    ) -> List[OHLC]:
        """
        Get today's intraday candles.

        Args:
            underlying: Index name
            interval: Candle interval (5minute, 15minute, etc.)

        Returns:
            List of intraday OHLC candles
        """
        today = date.today()
        return await self.get_ohlc(underlying, interval, today, today)

    async def get_recent_candles(
        self,
        underlying: str,
        interval: str,
        count: int = 100
    ) -> List[OHLC]:
        """
        Get most recent N candles.

        Args:
            underlying: Index name
            interval: Candle interval
            count: Number of candles to fetch

        Returns:
            List of recent OHLC candles (oldest first)
        """
        to_date = date.today()

        # Estimate from_date based on interval and count
        if interval == "day":
            days_back = count * 2  # Account for weekends
        elif interval in ["5minute", "15minute"]:
            days_back = min(count // 75, 30)  # ~75 5-min candles per day, max 30 days
        else:
            days_back = min(count // 30, 30)  # Estimate

        from_date = to_date - timedelta(days=max(days_back, 7))

        candles = await self.get_ohlc(underlying, interval, from_date, to_date)

        # Return only the requested number
        return candles[-count:] if len(candles) > count else candles

    async def _get_from_cache(self, key: str) -> Optional[List[dict]]:
        """Get data from Redis cache or memory fallback."""
        try:
            if self.redis:
                cached = await self.redis.get(key)
                if cached:
                    return json.loads(cached)
            else:
                # Fallback to memory cache
                if key in self._memory_cache:
                    return self._memory_cache[key]
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _save_to_cache(self, key: str, data: List[dict], ttl: int):
        """Save data to Redis cache or memory fallback."""
        try:
            if self.redis:
                await self.redis.setex(key, ttl, json.dumps(data))
            else:
                # Fallback to memory cache (no TTL enforcement in memory)
                self._memory_cache[key] = data
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
