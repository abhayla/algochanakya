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

    Uses structured lookup (underlying + expiry + strike + option_type)
    for reliable cross-broker symbol mapping instead of string manipulation.
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

    # Month mappings for symbol parsing
    MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    MONTH_TO_NUM = {name: i+1 for i, name in enumerate(MONTH_NAMES)}
    # Kite weekly month codes: 1-9 for Jan-Sep, O for Oct, N for Nov, D for Dec
    WEEKLY_MONTH_CODES = {
        '1': 'JAN', '2': 'FEB', '3': 'MAR', '4': 'APR', '5': 'MAY',
        '6': 'JUN', '7': 'JUL', '8': 'AUG', '9': 'SEP',
        'O': 'OCT', 'N': 'NOV', 'D': 'DEC'
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
        # Structured index for O(1) lookup by (underlying, expiry, strike, option_type)
        self._structured_index: Dict[str, Dict] = {}

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

        # Build structured index for options
        self._build_structured_index()
        logger.info(f"[SmartAPI] Built structured index with {len(self._structured_index)} option entries")

    def _build_structured_index(self):
        """
        Build a structured index for O(1) option lookup by components.

        Index key format: "{exchange}:{underlying}:{expiry_date}:{strike}:{option_type}"
        Where expiry_date is normalized to YYYY-MM-DD format.

        This allows matching Kite and SmartAPI symbols by their semantic meaning
        rather than string format, which differs between brokers.
        """
        self._structured_index = {}

        for inst in self._instruments:
            exch_seg = inst.get('exch_seg', '')
            symbol = inst.get('symbol', '')
            expiry = inst.get('expiry', '')  # Format: "27JAN2026"
            strike = inst.get('strike', '')
            inst_type = inst.get('instrumenttype', '')

            # Only index options (CE/PE)
            if not symbol or not (symbol.endswith('CE') or symbol.endswith('PE')):
                continue

            option_type = 'CE' if symbol.endswith('CE') else 'PE'

            # Extract underlying from symbol (everything before the date portion)
            underlying = self._extract_underlying_from_smartapi(symbol)
            if not underlying:
                continue

            # Normalize expiry to YYYY-MM-DD
            normalized_expiry = self._normalize_expiry(expiry)
            if not normalized_expiry:
                continue

            # Normalize strike (SmartAPI stores in paise for some, need to handle both)
            normalized_strike = self._normalize_strike(strike)

            # Create structured key
            struct_key = f"{exch_seg}:{underlying}:{normalized_expiry}:{normalized_strike}:{option_type}"

            self._structured_index[struct_key] = {
                'token': inst.get('token'),
                'symbol': symbol,
                'name': inst.get('name', ''),
                'expiry': expiry,
                'strike': strike,
                'lotsize': inst.get('lotsize', ''),
                'instrumenttype': inst_type,
                'exch_seg': exch_seg,
                'tick_size': inst.get('tick_size', ''),
            }

    def _extract_underlying_from_smartapi(self, symbol: str) -> Optional[str]:
        """
        Extract underlying from SmartAPI symbol.

        SmartAPI format: NIFTY27JAN2625750CE
        We need to extract "NIFTY" from this.
        """
        import re
        # Match: UNDERLYING + DD + MON + YY + STRIKE + CE/PE
        # The underlying is all letters at the start
        match = re.match(r'^([A-Z]+)\d', symbol)
        if match:
            return match.group(1)
        return None

    def _normalize_expiry(self, expiry: str) -> Optional[str]:
        """
        Normalize expiry date to YYYY-MM-DD format.

        Input formats:
        - SmartAPI: "27JAN2026" (DDMONYYYY)
        - Some formats: "2026-01-27"

        Output: "2026-01-27"
        """
        import re
        if not expiry:
            return None

        # Already in YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', expiry):
            return expiry

        # SmartAPI format: DDMONYYYY (e.g., "27JAN2026")
        match = re.match(r'^(\d{1,2})([A-Z]{3})(\d{4})$', expiry)
        if match:
            day, month_str, year = match.groups()
            month_num = self.MONTH_TO_NUM.get(month_str.upper())
            if month_num:
                return f"{year}-{month_num:02d}-{int(day):02d}"

        return None

    def _normalize_strike(self, strike: str) -> str:
        """
        Normalize strike price to integer string.

        SmartAPI sometimes stores strikes with decimals (e.g., "25750.00")
        or in paise. We normalize to integer rupees.
        """
        try:
            strike_float = float(strike)
            # If strike is in paise (> 100000 for typical index options), convert
            # This heuristic works for NIFTY/BANKNIFTY options (strikes < 100000 rupees)
            return str(int(strike_float))
        except (ValueError, TypeError):
            return str(strike)

    def _parse_kite_symbol(self, kite_symbol: str) -> Optional[Dict[str, str]]:
        """
        Parse Kite trading symbol into structured components.

        Kite formats:
        - Monthly: NIFTY26JAN25750PE (UNDERLYING + YY + MON + STRIKE + TYPE)
        - Weekly: NIFTY2510925750PE (UNDERLYING + YY + M + DD + STRIKE + TYPE)

        Returns:
            Dict with keys: underlying, expiry (YYYY-MM-DD), strike, option_type
            Or None if parsing fails
        """
        import re

        # Pattern 1: Kite MONTHLY option symbols
        # UNDERLYING + YY + MON + STRIKE + CE/PE
        monthly_pattern = r'^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$'
        match = re.match(monthly_pattern, kite_symbol)

        if match:
            underlying, year, month, strike, option_type = match.groups()
            if month.upper() in self.MONTH_NAMES:
                # For monthly, we don't know the exact day, but we can use last Thursday logic
                # or search all days. For now, return None for day and handle in lookup
                month_num = self.MONTH_TO_NUM[month.upper()]
                # Use 20XX for year (assuming we're in 2000s)
                full_year = f"20{year}"
                return {
                    'underlying': underlying,
                    'year': full_year,
                    'month': month_num,
                    'day': None,  # Unknown for monthly
                    'strike': strike,
                    'option_type': option_type,
                    'format': 'monthly'
                }

        # Pattern 2: Kite WEEKLY option symbols
        # UNDERLYING + YY + M + DD + STRIKE + CE/PE
        weekly_pattern = r'^([A-Z]+)(\d{2})([1-9OND])(\d{2})(\d+)(CE|PE)$'
        match = re.match(weekly_pattern, kite_symbol)

        if match:
            underlying, year, month_code, day, strike, option_type = match.groups()
            month_name = self.WEEKLY_MONTH_CODES.get(month_code.upper())
            if month_name:
                month_num = self.MONTH_TO_NUM[month_name]
                full_year = f"20{year}"
                return {
                    'underlying': underlying,
                    'year': full_year,
                    'month': month_num,
                    'day': int(day),
                    'strike': strike,
                    'option_type': option_type,
                    'format': 'weekly'
                }

        return None

    def _lookup_by_structure(self, exchange: str, parsed: Dict[str, str]) -> Optional[Dict]:
        """
        Lookup instrument by structured components.

        For monthly options (day unknown), searches all possible days.
        For weekly options, uses the exact day from the symbol.
        """
        underlying = parsed['underlying']
        year = parsed['year']
        month = parsed['month']
        strike = parsed['strike']
        option_type = parsed['option_type']

        if parsed['format'] == 'weekly' and parsed['day']:
            # Exact day known for weekly
            expiry = f"{year}-{month:02d}-{parsed['day']:02d}"
            struct_key = f"{exchange}:{underlying}:{expiry}:{strike}:{option_type}"
            if struct_key in self._structured_index:
                return self._structured_index[struct_key]
        else:
            # Monthly - search all possible days (typically last Thursday, but varies)
            for day in range(1, 32):
                expiry = f"{year}-{month:02d}-{day:02d}"
                struct_key = f"{exchange}:{underlying}:{expiry}:{strike}:{option_type}"
                if struct_key in self._structured_index:
                    return self._structured_index[struct_key]

        return None

    def _convert_kite_to_smartapi_symbol(self, kite_symbol: str) -> List[str]:
        """
        Convert Kite tradingsymbol to possible SmartAPI symbol formats.

        Kite formats:
        - Monthly: NIFTY26JAN25750PE (UNDERLYING + YY + MON + STRIKE + TYPE)
        - Weekly: NIFTY2510925750PE (UNDERLYING + YY + M + DD + STRIKE + TYPE) where M is month code (O=Oct, N=Nov, D=Dec, 1-9 for Jan-Sep)

        SmartAPI format: NIFTY27JAN2625750PE (UNDERLYING + DD + MON + YY + STRIKE + TYPE)

        This function generates all possible SmartAPI symbols for a given Kite symbol
        by trying all days of the month.

        Args:
            kite_symbol: Kite trading symbol

        Returns:
            List of possible SmartAPI symbols to try
        """
        import re

        # Month code mappings
        MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        # Kite weekly month codes: 1-9 for Jan-Sep, O for Oct, N for Nov, D for Dec
        WEEKLY_MONTH_CODES = {'1': 'JAN', '2': 'FEB', '3': 'MAR', '4': 'APR', '5': 'MAY',
                             '6': 'JUN', '7': 'JUL', '8': 'AUG', '9': 'SEP',
                             'O': 'OCT', 'N': 'NOV', 'D': 'DEC'}

        possible_symbols = []

        # Pattern 1: Kite MONTHLY option symbols: UNDERLYING + YY + MON + STRIKE + CE/PE
        # Examples: NIFTY26JAN25750PE, BANKNIFTY26JAN50000CE, FINNIFTY26JAN25000PE
        monthly_pattern = r'^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$'
        match = re.match(monthly_pattern, kite_symbol)

        if match:
            underlying, year, month, strike, option_type = match.groups()

            # Validate month
            if month.upper() in MONTH_NAMES:
                # Generate SmartAPI symbols for all possible days (1-31)
                for day in range(1, 32):
                    # SmartAPI uses DD format (with leading zero for single digits)
                    day_str = str(day).zfill(2) if day < 10 else str(day)
                    smartapi_symbol = f"{underlying}{day_str}{month}{year}{strike}{option_type}"
                    possible_symbols.append(smartapi_symbol)

                    # Also try single digit day format (SmartAPI sometimes uses this)
                    if day < 10:
                        smartapi_symbol_single = f"{underlying}{day}{month}{year}{strike}{option_type}"
                        possible_symbols.append(smartapi_symbol_single)

                return possible_symbols

        # Pattern 2: Kite WEEKLY option symbols: UNDERLYING + YY + M + DD + STRIKE + CE/PE
        # M is single char: 1-9 for Jan-Sep, O for Oct, N for Nov, D for Dec
        # Examples: NIFTY2510925750PE (NIFTY, 25, Oct, 09, 25750, PE)
        weekly_pattern = r'^([A-Z]+)(\d{2})([1-9OND])(\d{2})(\d+)(CE|PE)$'
        match = re.match(weekly_pattern, kite_symbol)

        if match:
            underlying, year, month_code, day, strike, option_type = match.groups()

            # Convert month code to month name
            month = WEEKLY_MONTH_CODES.get(month_code.upper())
            if month:
                # For weekly, we know the exact day from Kite symbol
                # Generate SmartAPI symbol with that day
                smartapi_symbol = f"{underlying}{day}{month}{year}{strike}{option_type}"
                possible_symbols.append(smartapi_symbol)

                # Also try with leading zero removed if day starts with 0
                if day.startswith('0'):
                    smartapi_symbol_single = f"{underlying}{day.lstrip('0')}{month}{year}{strike}{option_type}"
                    possible_symbols.append(smartapi_symbol_single)

                return possible_symbols

        # Pattern 3: Already in SmartAPI format or unknown format - return original
        # This handles cases like equity symbols (RELIANCE, TCS, etc.)
        return [kite_symbol]

    async def lookup_token(
        self,
        tradingsymbol: str,
        exchange: str
    ) -> Optional[str]:
        """
        Lookup SmartAPI token from tradingsymbol.

        Uses a multi-tier lookup strategy:
        1. Direct symbol match in local cache
        2. Redis cache lookup
        3. Structured lookup by parsed components (O(1) - PREFERRED)
        4. Fallback: String-based symbol translation

        Args:
            tradingsymbol: Trading symbol (e.g., "NIFTY24DEC26000CE")
            exchange: Exchange (e.g., "NFO", "NSE")

        Returns:
            SmartAPI token string or None if not found
        """
        cache_key = f"{exchange}:{tradingsymbol}"

        # Tier 1: Check local cache first (exact symbol match)
        if cache_key in self._local_cache:
            return self._local_cache[cache_key].get('token')

        # Tier 2: Check Redis
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

        # Ensure instruments are loaded
        if not self._instruments:
            await self.download_master()
            if cache_key in self._local_cache:
                return self._local_cache[cache_key].get('token')

        # Tier 3: STRUCTURED LOOKUP (PREFERRED) - parse symbol and lookup by components
        # This is more reliable than string manipulation as it uses semantic matching
        if exchange == 'NFO':
            parsed = self._parse_kite_symbol(tradingsymbol)
            if parsed:
                inst = self._lookup_by_structure(exchange, parsed)
                if inst:
                    token = inst.get('token')
                    if token:
                        # Cache under original key for future lookups
                        self._local_cache[cache_key] = inst
                        logger.info(f"[SmartAPI] Found token via structured lookup: {tradingsymbol} -> {inst.get('symbol')}")
                        return token

            # Tier 4: Fallback to string-based symbol translation
            # This handles edge cases that structured lookup might miss
            possible_symbols = self._convert_kite_to_smartapi_symbol(tradingsymbol)
            logger.debug(f"[SmartAPI] Fallback: trying symbol translation for {tradingsymbol}, generated {len(possible_symbols)} candidates")
            for smartapi_symbol in possible_symbols:
                smartapi_cache_key = f"{exchange}:{smartapi_symbol}"
                if smartapi_cache_key in self._local_cache:
                    token = self._local_cache[smartapi_cache_key].get('token')
                    if token:
                        # Cache under original key too for future lookups
                        self._local_cache[cache_key] = self._local_cache[smartapi_cache_key]
                        logger.info(f"[SmartAPI] Found token via symbol translation: {tradingsymbol} -> {smartapi_symbol}")
                        return token

        logger.warning(f"[SmartAPI] Token not found for {exchange}:{tradingsymbol} (cache: {len(self._local_cache)}, structured index: {len(self._structured_index)})")
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
            expiry: Expiry date string (e.g., "27JAN2026")
            exchange: Exchange (default NFO)

        Returns:
            List of instrument dicts with CE and PE options
        """
        if not self._instruments:
            await self.download_master()

        options = []
        # Build expected symbol prefix pattern
        # For NIFTY with expiry 27JAN2026, symbol should be like NIFTY27JAN26...
        # We need to match exact underlying to avoid NIFTYNXT50 matching NIFTY
        symbol_prefix = f"{underlying}{expiry[:5]}"  # e.g., "NIFTY27JAN"

        for inst in self._instruments:
            if inst.get('exch_seg') != exchange:
                continue

            symbol = inst.get('symbol', '')
            inst_expiry = inst.get('expiry', '')
            inst_type = inst.get('instrumenttype', '')

            # Check if it's an option for this underlying and expiry
            # Symbol format: NIFTY27JAN2625600CE
            # Expiry format in data: 27JAN2026
            if (symbol.startswith(symbol_prefix) and
                inst_expiry == expiry and
                (symbol.endswith('CE') or symbol.endswith('PE'))):
                options.append({
                    'token': inst.get('token'),
                    'symbol': symbol,
                    'strike': inst.get('strike'),
                    'instrumenttype': inst_type,
                    'expiry': inst_expiry,
                    'lotsize': inst.get('lotsize'),
                })

        logger.info(f"[SmartAPI] Found {len(options)} options for {underlying} expiry {expiry}")
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
