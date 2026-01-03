"""
SmartAPI Instruments Service

Handles instrument master download and token lookup for AngelOne SmartAPI.
SmartAPI uses different instrument tokens than Kite, so we need to map
tradingsymbols to SmartAPI tokens.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import httpx
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class SmartAPIInstruments:
    """
    Instrument master service for SmartAPI token lookup.

    Downloads and caches the instrument master from AngelOne.
    Provides O(1) lookup by tradingsymbol and exchange.
    """

    MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    CACHE_TTL = 86400  # 24 hours
    CACHE_PREFIX = "smartapi:instrument:"

    # Exchange type mapping for SmartAPI
    EXCHANGE_TYPES = {
        'NSE': 1,   # NSE Cash
        'NFO': 2,   # NSE F&O
        'BSE': 3,   # BSE Cash
        'BFO': 4,   # BSE F&O
        'MCX': 5,   # MCX
        'CDS': 7,   # Currency Derivatives
    }

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize instruments service.

        Args:
            redis_client: Optional Redis client for caching
        """
        self._redis = redis_client
        self._local_cache: Dict[str, Dict] = {}  # Fallback in-memory cache
        self._last_download: Optional[datetime] = None
        self._instruments: List[Dict] = []

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client, creating if needed."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
            except Exception as e:
                logger.warning(f"Redis not available, using local cache: {e}")
        return self._redis

    async def download_master(self, force: bool = False) -> int:
        """
        Download instrument master from AngelOne.

        Args:
            force: Force download even if cache is fresh

        Returns:
            Number of instruments downloaded
        """
        # Check if we need to refresh
        if not force and self._last_download:
            if datetime.now() - self._last_download < timedelta(hours=12):
                logger.info("[SmartAPI] Instrument master still fresh, skipping download")
                return len(self._instruments)

        try:
            logger.info("[SmartAPI] Downloading instrument master...")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.MASTER_URL)
                response.raise_for_status()
                instruments = response.json()

            self._instruments = instruments
            self._last_download = datetime.now()

            # Cache instruments by symbol+exchange for fast lookup
            await self._cache_instruments(instruments)

            logger.info(f"[SmartAPI] Downloaded {len(instruments)} instruments")
            return len(instruments)

        except Exception as e:
            logger.error(f"[SmartAPI] Failed to download instrument master: {e}")
            raise

    async def _cache_instruments(self, instruments: List[Dict]):
        """
        Cache instruments in Redis and local memory.

        Args:
            instruments: List of instrument dictionaries from master
        """
        redis_client = await self._get_redis()
        pipe = redis_client.pipeline() if redis_client else None

        for inst in instruments:
            symbol = inst.get('symbol', '')
            exch_seg = inst.get('exch_seg', '')
            token = inst.get('token', '')

            if not symbol or not exch_seg or not token:
                continue

            # Create cache key
            cache_key = f"{self.CACHE_PREFIX}{exch_seg}:{symbol}"

            # Store full instrument data
            inst_data = {
                'token': token,
                'symbol': symbol,
                'name': inst.get('name', ''),
                'expiry': inst.get('expiry', ''),
                'strike': inst.get('strike', ''),
                'lotsize': inst.get('lotsize', ''),
                'instrumenttype': inst.get('instrumenttype', ''),
                'exch_seg': exch_seg,
                'tick_size': inst.get('tick_size', ''),
            }

            # Store in local cache
            self._local_cache[f"{exch_seg}:{symbol}"] = inst_data

            # Store in Redis if available
            if pipe:
                import json
                pipe.setex(cache_key, self.CACHE_TTL, json.dumps(inst_data))

        # Execute Redis pipeline
        if pipe:
            try:
                await pipe.execute()
            except Exception as e:
                logger.warning(f"[SmartAPI] Redis cache failed: {e}")

    async def lookup_token(
        self,
        tradingsymbol: str,
        exchange: str
    ) -> Optional[str]:
        """
        Lookup SmartAPI token from tradingsymbol.

        Args:
            tradingsymbol: Trading symbol (e.g., "NIFTY24DEC26000CE")
            exchange: Exchange (e.g., "NFO", "NSE")

        Returns:
            SmartAPI token string or None if not found
        """
        cache_key = f"{exchange}:{tradingsymbol}"

        # Check local cache first
        if cache_key in self._local_cache:
            return self._local_cache[cache_key].get('token')

        # Check Redis
        redis_client = await self._get_redis()
        if redis_client:
            try:
                import json
                data = await redis_client.get(f"{self.CACHE_PREFIX}{cache_key}")
                if data:
                    inst = json.loads(data)
                    self._local_cache[cache_key] = inst  # Update local cache
                    return inst.get('token')
            except Exception as e:
                logger.warning(f"[SmartAPI] Redis lookup failed: {e}")

        # If not in cache, try downloading master
        if not self._instruments:
            await self.download_master()
            if cache_key in self._local_cache:
                return self._local_cache[cache_key].get('token')

        logger.warning(f"[SmartAPI] Token not found for {exchange}:{tradingsymbol}")
        return None

    async def lookup_instrument(
        self,
        tradingsymbol: str,
        exchange: str
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup full instrument data from tradingsymbol.

        Args:
            tradingsymbol: Trading symbol
            exchange: Exchange

        Returns:
            Full instrument data dict or None if not found
        """
        cache_key = f"{exchange}:{tradingsymbol}"

        # Check local cache
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        # Trigger lookup which will populate cache
        await self.lookup_token(tradingsymbol, exchange)
        return self._local_cache.get(cache_key)

    async def lookup_by_token(
        self,
        token: str,
        exchange: str
    ) -> Optional[Dict[str, Any]]:
        """
        Reverse lookup: find instrument by SmartAPI token.

        Args:
            token: SmartAPI instrument token
            exchange: Exchange

        Returns:
            Instrument data dict or None if not found
        """
        # Ensure instruments are loaded
        if not self._instruments:
            await self.download_master()

        # Search in instruments list
        for inst in self._instruments:
            if inst.get('token') == token and inst.get('exch_seg') == exchange:
                return {
                    'token': token,
                    'symbol': inst.get('symbol', ''),
                    'name': inst.get('name', ''),
                    'expiry': inst.get('expiry', ''),
                    'strike': inst.get('strike', ''),
                    'lotsize': inst.get('lotsize', ''),
                    'instrumenttype': inst.get('instrumenttype', ''),
                    'exch_seg': exchange,
                }

        return None

    def get_exchange_type(self, exchange: str) -> int:
        """
        Get SmartAPI exchange type code.

        Args:
            exchange: Exchange name (NSE, NFO, etc.)

        Returns:
            Exchange type integer for SmartAPI
        """
        return self.EXCHANGE_TYPES.get(exchange.upper(), 1)

    async def get_option_chain_tokens(
        self,
        underlying: str,
        expiry: str,
        exchange: str = "NFO"
    ) -> List[Dict[str, Any]]:
        """
        Get all option tokens for an underlying and expiry.

        Args:
            underlying: Underlying symbol (e.g., "NIFTY", "BANKNIFTY")
            expiry: Expiry date string (e.g., "26DEC2024")
            exchange: Exchange (default NFO)

        Returns:
            List of instrument dicts with CE and PE options
        """
        if not self._instruments:
            await self.download_master()

        options = []
        for inst in self._instruments:
            if inst.get('exch_seg') != exchange:
                continue

            symbol = inst.get('symbol', '')
            inst_expiry = inst.get('expiry', '')
            inst_type = inst.get('instrumenttype', '')

            # Check if it's an option for this underlying and expiry
            if (inst_type in ['CE', 'PE', 'OPTIDX'] and
                symbol.startswith(underlying) and
                expiry in inst_expiry):
                options.append({
                    'token': inst.get('token'),
                    'symbol': symbol,
                    'strike': inst.get('strike'),
                    'option_type': 'CE' if 'CE' in symbol else 'PE',
                    'expiry': inst_expiry,
                    'lotsize': inst.get('lotsize'),
                })

        return options

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Global singleton instance
_smartapi_instruments: Optional[SmartAPIInstruments] = None


def get_smartapi_instruments() -> SmartAPIInstruments:
    """Get the global SmartAPI instruments service instance."""
    global _smartapi_instruments
    if _smartapi_instruments is None:
        _smartapi_instruments = SmartAPIInstruments()
    return _smartapi_instruments
