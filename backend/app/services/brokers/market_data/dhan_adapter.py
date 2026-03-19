"""
Dhan Market Data Adapter

Wraps Dhan REST API for market data operations in the unified
MarketDataBrokerAdapter interface.

Key characteristics:
- Uses numeric security_id for all API calls (no string symbols)
- All prices in RUPEES natively (no paise conversion needed)
- Auth header: 'access-token' (hyphenated lowercase)
- Market data endpoints use POST with JSON body (not GET)
- Historical response is parallel arrays, not array-of-objects
- Two endpoints for historical: /charts/historical (daily) and /charts/intraday (sub-daily)
- Instrument master downloaded from CSV: images.dhan.co/api-data/api-scrip-master.csv

Key responsibilities:
- get_quote via POST /v2/marketfeed/quote (full quote with 20-depth)
- get_ltp via POST /v2/marketfeed/ltp
- get_historical via POST /v2/charts/historical (daily) or /v2/charts/intraday (intraday)
- get_instruments by downloading and parsing Dhan CSV instrument master
- Token mapping via TokenManager (canonical <-> security_id)
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import List, Dict, Optional, Callable

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    DhanMarketDataCredentials,
    OHLCVCandle,
    Instrument,
)
from app.services.brokers.base import UnifiedQuote
from app.services.brokers.market_data.exceptions import (
    BrokerAPIError,
    InvalidSymbolError,
    DataNotAvailableError,
    AuthenticationError,
)
from app.services.brokers.market_data.token_manager import TokenManagerFactory

logger = logging.getLogger(__name__)

# Dhan REST API base URL
DHAN_API_BASE = "https://api.dhan.co/v2"

# Instrument CSV URL (daily updated)
DHAN_INSTRUMENT_CSV_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Exchange mapping: canonical exchange codes -> Dhan segment strings
_EXCHANGE_TO_SEGMENT = {
    "NFO": "NSE_FNO",
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "BFO": "BSE_FNO",
    "MCX": "MCX_COMM",
    "IDX": "IDX_I",
    # Dhan native formats pass through unchanged
    "NSE_EQ": "NSE_EQ",
    "NSE_FNO": "NSE_FNO",
    "BSE_EQ": "BSE_EQ",
    "BSE_FNO": "BSE_FNO",
    "MCX_COMM": "MCX_COMM",
    "IDX_I": "IDX_I",
}

# Segment to canonical exchange code
_SEGMENT_TO_EXCHANGE = {
    "NSE_EQ": "NSE",
    "NSE_FNO": "NFO",
    "BSE_EQ": "BSE",
    "BSE_FNO": "BFO",
    "MCX_COMM": "MCX",
    "IDX_I": "NSE",
}

# Interval mapping: canonical -> Dhan intraday interval string
_INTRADAY_INTERVAL_MAP = {
    "1min": "1",
    "5min": "5",
    "15min": "15",
    "25min": "25",
    "hour": "60",
}

# Intraday intervals (sub-daily) use /charts/intraday; "day" uses /charts/historical
_INTRADAY_INTERVALS = set(_INTRADAY_INTERVAL_MAP.keys())

# Dhan instrument type -> instrument_type field
_INSTRUMENT_TYPE_MAP = {
    "EQUITY": "EQ",
    "OPTIDX": "CE",   # will be overridden by SEM_OPTION_TYPE
    "OPTSTK": "CE",   # will be overridden by SEM_OPTION_TYPE
    "FUTIDX": "FUT",
    "FUTSTK": "FUT",
}


class DhanMarketDataAdapter(MarketDataBrokerAdapter):
    """
    Dhan market data adapter for quotes, historical data, and instruments.

    Wraps Dhan REST API v2. All prices are in RUPEES (no conversion needed).
    Symbols are converted between canonical (Kite) format and Dhan security_id.
    """

    def __init__(self, credentials: DhanMarketDataCredentials, db: AsyncSession):
        """
        Initialize Dhan adapter.

        Args:
            credentials: Dhan credentials (client_id, access_token)
            db: Database session for token lookups
        """
        super().__init__(credentials)
        self.db = db
        self._token_manager = TokenManagerFactory.get_manager("dhan", db)
        self._ticker_callbacks: List[Callable] = []

        # HTTP headers for all requests
        self._headers = {
            "access-token": credentials.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def broker_type(self) -> MarketDataBrokerType:
        return MarketDataBrokerType.DHAN

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes (OHLC + volume + OI + 20-depth) for canonical symbols.

        Args:
            symbols: List of canonical symbols (e.g., NIFTY26FEB24000CE)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote (prices in RUPEES)
        """
        try:
            # Build security_id grouped by exchange segment
            body, id_to_canonical = await self._build_market_feed_body(symbols)
            if not body:
                return {}

            raw = await self._make_request("POST", "/marketfeed/quote", body=body)

            unified_quotes = {}
            data = raw.get("data", {})
            for segment, instruments in data.items():
                for security_id_str, raw_data in instruments.items():
                    canonical = id_to_canonical.get(f"{segment}:{security_id_str}")
                    if canonical:
                        unified_quotes[canonical] = self._convert_to_unified_quote(
                            raw_data, canonical, _SEGMENT_TO_EXCHANGE.get(segment, "NFO")
                        )

            return unified_quotes

        except (AuthenticationError, InvalidSymbolError, DataNotAvailableError):
            raise
        except Exception as e:
            logger.error(f"[Dhan] get_quote error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("dhan", str(e))
            raise BrokerAPIError("dhan", f"Failed to get quotes: {str(e)}")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only for canonical symbols.

        Args:
            symbols: List of canonical symbols

        Returns:
            Dict mapping canonical symbol to LTP in RUPEES
        """
        try:
            body, id_to_canonical = await self._build_market_feed_body(symbols)
            if not body:
                return {}

            raw = await self._make_request("POST", "/marketfeed/ltp", body=body)

            ltp_map = {}
            data = raw.get("data", {})
            for segment, instruments in data.items():
                for security_id_str, raw_data in instruments.items():
                    canonical = id_to_canonical.get(f"{segment}:{security_id_str}")
                    if canonical:
                        ltp = raw_data.get("last_price", 0)
                        ltp_map[canonical] = Decimal(str(ltp))

            return ltp_map

        except (AuthenticationError, InvalidSymbolError, DataNotAvailableError):
            raise
        except Exception as e:
            logger.error(f"[Dhan] get_ltp error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("dhan", str(e))
            raise BrokerAPIError("dhan", f"Failed to get LTP: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS (delegated to ticker adapter)
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """WebSocket managed separately via DhanTickerAdapter."""
        logger.warning("[Dhan] subscribe() called on REST adapter - WebSocket managed separately")

    async def unsubscribe(self, tokens: List[int]) -> None:
        """WebSocket managed separately via DhanTickerAdapter."""
        logger.warning("[Dhan] unsubscribe() called on REST adapter - WebSocket managed separately")

    def on_tick(self, callback: Callable) -> None:
        """Register callback for incoming ticks."""
        self._ticker_callbacks.append(callback)

    # ═══════════════════════════════════════════════════════════════════════
    # HISTORICAL DATA
    # ═══════════════════════════════════════════════════════════════════════

    async def get_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        interval: str = "day"
    ) -> List[OHLCVCandle]:
        """
        Get historical OHLCV candles.

        Uses /charts/intraday for sub-daily intervals (1min, 5min, 15min, hour).
        Uses /charts/historical for daily candles.

        Args:
            symbol: Canonical symbol (e.g., HDFCBANK, NIFTY26FEB24000CE)
            from_date: Start date
            to_date: End date
            interval: "1min", "5min", "15min", "hour", or "day"

        Returns:
            List of OHLCVCandle (prices in RUPEES)
        """
        try:
            token = await self._token_manager.get_token(symbol)
            if token is None:
                raise InvalidSymbolError(symbol, "dhan")

            security_id = str(token)
            exchange_segment = await self._get_segment_for_symbol(symbol)
            instrument_type = _get_instrument_type_str(exchange_segment)

            if interval in _INTRADAY_INTERVALS:
                return await self._get_intraday(
                    security_id, exchange_segment, instrument_type,
                    from_date, to_date, interval
                )
            else:
                return await self._get_daily(
                    security_id, exchange_segment, instrument_type,
                    from_date, to_date
                )

        except (InvalidSymbolError, DataNotAvailableError):
            raise
        except Exception as e:
            logger.error(f"[Dhan] get_historical error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("dhan", str(e))
            raise DataNotAvailableError("dhan", str(e))

    async def _get_daily(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: date,
        to_date: date,
    ) -> List[OHLCVCandle]:
        """Fetch daily candles from /charts/historical."""
        body = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "expiryCode": 0,
            "fromDate": from_date.strftime("%Y-%m-%d"),
            "toDate": to_date.strftime("%Y-%m-%d"),
        }
        raw = await self._make_request("POST", "/charts/historical", body=body)
        return _parse_parallel_array_response(raw, is_intraday=False)

    async def _get_intraday(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: date,
        to_date: date,
        interval: str,
    ) -> List[OHLCVCandle]:
        """Fetch intraday candles from /charts/intraday."""
        dhan_interval = _INTRADAY_INTERVAL_MAP.get(interval, "5")
        body = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "interval": dhan_interval,
            "fromDate": from_date.strftime("%Y-%m-%d"),
            "toDate": to_date.strftime("%Y-%m-%d"),
        }
        raw = await self._make_request("POST", "/charts/intraday", body=body)
        return _parse_parallel_array_response(raw, is_intraday=True)

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUMENTS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Get instruments by downloading and parsing Dhan's CSV master file.

        Args:
            exchange: Canonical exchange code (NFO, NSE, BSE, MCX)

        Returns:
            List of Instrument objects with canonical symbols
        """
        try:
            csv_content = await self._download_instrument_csv()
            return _parse_instrument_csv(csv_content, exchange)
        except Exception as e:
            logger.error(f"[Dhan] get_instruments error: {e}")
            raise BrokerAPIError("dhan", f"Failed to get instruments: {str(e)}")

    async def search_instruments(self, query: str) -> List[Instrument]:
        """
        Search instruments by name or symbol.

        Args:
            query: Search query (case-insensitive)

        Returns:
            Up to 50 matching Instrument objects
        """
        try:
            all_instruments = await self.get_instruments("NFO")
            query_lower = query.lower()
            matches = [
                inst for inst in all_instruments
                if query_lower in inst.name.lower() or query_lower in inst.canonical_symbol.lower()
            ]
            return matches[:50]
        except Exception as e:
            logger.error(f"[Dhan] search_instruments error: {e}")
            raise BrokerAPIError("dhan", f"Failed to search instruments: {str(e)}")

    async def get_token(self, symbol: str) -> int:
        """Get Dhan security_id (as int) for canonical symbol."""
        token = await self._token_manager.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(symbol, "dhan")
        return token

    async def get_symbol(self, token: int) -> str:
        """Get canonical symbol for Dhan security_id."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError(f"token:{token}", "dhan")
        return symbol

    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self) -> bool:
        """
        Validate credentials via GET /profile and load token cache.

        Returns:
            True if successful
        """
        try:
            profile = await self._make_request("GET", "/profile")
            client_id = profile.get("clientId", "Unknown")
            logger.info(f"[Dhan] Connected for client: {client_id}")

            await self._token_manager.load_cache()

            self._initialized = True
            logger.info("[Dhan] Adapter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[Dhan] Failed to connect: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("dhan", str(e))
            return False

    async def disconnect(self) -> None:
        """Close adapter (REST-only, nothing to disconnect)."""
        self._initialized = False
        logger.info("[Dhan] Adapter disconnected")

    @property
    def is_connected(self) -> bool:
        return self._initialized

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Make an authenticated request to the Dhan API.

        Args:
            method: HTTP method ("GET" or "POST")
            endpoint: API endpoint path (e.g., "/marketfeed/ltp")
            body: JSON request body (for POST)
            params: Query params (for GET)

        Returns:
            Parsed JSON response dict

        Raises:
            AuthenticationError: 401 response
            BrokerAPIError: Other HTTP errors
        """
        url = f"{DHAN_API_BASE}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=self._headers, params=params)
            else:
                response = await client.post(url, headers=self._headers, json=body)

            if response.status_code == 401:
                # Dhan market data API requires BOTH valid credentials AND a paid Data API
                # subscription (₹499/month or 25 F&O trades/month). Known error codes:
                #   806 = "Data APIs not Subscribed"
                #   810 = "ClientId is invalid"
                # Any 401 on market data endpoints means the account is not set up for
                # market data access — raise DataNotAvailableError so tests can skip.
                body_text = response.text
                if "806" in body_text:
                    raise DataNotAvailableError("dhan", f"Data APIs not subscribed (error 806). Subscribe at web.dhan.co → Profile → DhanHQ Trading APIs. Response: {body_text}")
                if "810" in body_text:
                    raise DataNotAvailableError("dhan", f"Invalid client ID (error 810). Check DHAN_CLIENT_ID in .env. Response: {body_text}")
                raise DataNotAvailableError("dhan", f"Market data access denied (HTTP 401). Check credentials and Data API subscription. Response: {body_text}")

            response.raise_for_status()
            return response.json()

    async def _build_market_feed_body(
        self, symbols: List[str]
    ) -> tuple[dict, dict]:
        """
        Build the POST body for /marketfeed/* endpoints.

        Dhan expects: {"NSE_FNO": [43854, 43855], "NSE_EQ": [1333]}

        Returns:
            (body_dict, id_to_canonical) where id_to_canonical maps
            "SEGMENT:security_id_str" -> canonical symbol
        """
        body: dict = {}
        id_to_canonical: dict = {}

        for symbol in symbols:
            token = await self._token_manager.get_token(symbol)
            if token is None:
                raise InvalidSymbolError(symbol, "dhan")

            security_id = int(token)
            exchange_segment = await self._get_segment_for_symbol(symbol)

            if exchange_segment not in body:
                body[exchange_segment] = []
            body[exchange_segment].append(security_id)

            id_to_canonical[f"{exchange_segment}:{security_id}"] = symbol

        return body, id_to_canonical

    async def _get_segment_for_symbol(self, symbol: str) -> str:
        """
        Determine Dhan exchange segment for a canonical symbol.

        Falls back to NSE_FNO for options/futures, NSE_EQ for equities.
        """
        # Options/futures contain digit sequences after the name
        # (e.g., NIFTY26FEB24000CE, BANKNIFTY26FEB51000PE)
        # Check if it has option/future suffix
        for suffix in ("CE", "PE", "FUT"):
            if symbol.endswith(suffix):
                return "NSE_FNO"

        # Indices
        if symbol in ("NIFTY 50", "NIFTY BANK", "SENSEX", "NIFTY50", "BANKNIFTY"):
            return "IDX_I"

        # Default to equity
        return "NSE_EQ"

    async def _download_instrument_csv(self) -> str:
        """Download Dhan instrument master CSV content."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(DHAN_INSTRUMENT_CSV_URL)
            response.raise_for_status()
            return response.text

    def _convert_to_unified_quote(
        self, raw_data: dict, canonical_symbol: str, exchange: str
    ) -> UnifiedQuote:
        """
        Convert Dhan quote response to UnifiedQuote.

        Dhan prices are already in RUPEES — no conversion needed.
        """
        last_price = Decimal(str(raw_data.get("last_price", 0)))
        close_price = Decimal(str(raw_data.get("close", 0)))

        # Extract best bid/ask from depth arrays
        bid_list = raw_data.get("bid", [])
        ask_list = raw_data.get("ask", [])
        best_bid = bid_list[0] if bid_list else {}
        best_ask = ask_list[0] if ask_list else {}

        # Parse last_trade_time
        ltt_str = raw_data.get("last_trade_time", "")
        try:
            ltt = datetime.fromisoformat(ltt_str) if ltt_str else datetime.now()
        except (ValueError, TypeError):
            ltt = datetime.now()

        return UnifiedQuote(
            tradingsymbol=canonical_symbol,
            exchange=exchange,
            instrument_token=None,  # Dhan security_id not stored here
            last_price=last_price,
            open=Decimal(str(raw_data.get("open", 0))),
            high=Decimal(str(raw_data.get("high", 0))),
            low=Decimal(str(raw_data.get("low", 0))),
            close=close_price,
            change=last_price - close_price,
            change_percent=Decimal("0"),
            volume=raw_data.get("volume", 0),
            oi=raw_data.get("oi", 0),
            bid_price=Decimal(str(best_bid.get("price", 0))),
            bid_quantity=best_bid.get("quantity", 0),
            ask_price=Decimal(str(best_ask.get("price", 0))),
            ask_quantity=best_ask.get("quantity", 0),
            last_trade_time=ltt,
            raw_response=raw_data,
        )

    def _get_exchange_segment(self, exchange: str) -> str:
        """Convert canonical exchange code to Dhan segment string."""
        return _EXCHANGE_TO_SEGMENT.get(exchange, "NSE_EQ")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL HELPERS (pure functions, testable)
# ═══════════════════════════════════════════════════════════════════════════════

def _is_auth_error(e: Exception) -> bool:
    """Check if exception is auth-related."""
    msg = str(e).lower()
    return any(kw in msg for kw in ("unauthorized", "token", "access-token", "401", "forbidden"))


def _get_instrument_type_str(exchange_segment: str) -> str:
    """Map exchange segment to Dhan instrument type string for historical API."""
    if exchange_segment in ("NSE_FNO", "BSE_FNO"):
        return "FUTOPT"
    if exchange_segment == "IDX_I":
        return "INDEX"
    return "EQUITY"


def _parse_parallel_array_response(
    raw: dict, is_intraday: bool
) -> List[OHLCVCandle]:
    """
    Parse Dhan's parallel-array historical response into OHLCVCandle list.

    Dhan returns:
        {"open": [...], "high": [...], "low": [...], "close": [...],
         "volume": [...], "timestamp": [...]}

    Each index corresponds to one candle. Prices already in RUPEES.
    """
    opens = raw.get("open", [])
    highs = raw.get("high", [])
    lows = raw.get("low", [])
    closes = raw.get("close", [])
    volumes = raw.get("volume", [])
    timestamps = raw.get("timestamp", [])

    candles = []
    for i, ts_str in enumerate(timestamps):
        try:
            if is_intraday:
                # Intraday: "2026-02-13 09:15:00"
                ts = datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S")
            else:
                # Daily: "2026-01-01"
                ts = datetime.strptime(str(ts_str), "%Y-%m-%d")
        except (ValueError, TypeError):
            try:
                ts = datetime.fromisoformat(str(ts_str))
            except (ValueError, TypeError):
                ts = datetime.now()

        candles.append(OHLCVCandle(
            timestamp=ts,
            open=Decimal(str(opens[i])) if i < len(opens) else Decimal("0"),
            high=Decimal(str(highs[i])) if i < len(highs) else Decimal("0"),
            low=Decimal(str(lows[i])) if i < len(lows) else Decimal("0"),
            close=Decimal(str(closes[i])) if i < len(closes) else Decimal("0"),
            volume=int(volumes[i]) if i < len(volumes) else 0,
            raw_response=None,
        ))

    return candles


def _parse_instrument_csv(csv_content: str, exchange: str = "NFO") -> List[Instrument]:
    """
    Parse Dhan instrument CSV into Instrument objects.

    Converts Dhan trading symbols to canonical (Kite) format.
    Filters by exchange: "NFO" -> NSE_FNO, "NSE" -> NSE_EQ, etc.
    """
    import csv as csv_module

    # Map exchange filter to segment(s)
    target_segments = {
        "NFO": {"NSE_FNO"},
        "BFO": {"BSE_FNO"},
        "NSE": {"NSE_EQ"},
        "BSE": {"BSE_EQ"},
        "MCX": {"MCX_COMM"},
    }.get(exchange, {"NSE_FNO", "NSE_EQ"})

    instruments = []
    reader = csv_module.DictReader(StringIO(csv_content))

    for row in reader:
        try:
            # Determine Dhan segment for this row
            dhan_segment = _row_to_segment(row)
            if dhan_segment not in target_segments:
                continue

            canonical = _row_to_canonical_symbol(row)
            if not canonical:
                continue

            instrument_name = row.get("SEM_INSTRUMENT_NAME", "EQUITY")
            instrument_type = _INSTRUMENT_TYPE_MAP.get(instrument_name, "EQ")

            # For options, override type with actual option type
            if instrument_name in ("OPTIDX", "OPTSTK"):
                instrument_type = row.get("SEM_OPTION_TYPE", "CE") or "CE"

            # Parse optional fields
            strike = None
            strike_str = row.get("SEM_STRIKE_PRICE", "")
            if strike_str:
                try:
                    strike = Decimal(str(float(strike_str)))
                except (ValueError, TypeError):
                    pass

            expiry = None
            expiry_str = row.get("SEM_EXPIRY_DATE", "")
            if expiry_str:
                try:
                    expiry = datetime.strptime(expiry_str.strip(), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass

            lot_size = 1
            lot_str = row.get("SEM_LOT_SIZE", "1")
            if lot_str:
                try:
                    lot_size = int(float(lot_str))
                except (ValueError, TypeError):
                    pass

            tick_size = Decimal("0.05")
            tick_str = row.get("SEM_TICK_SIZE", "0.05")
            if tick_str:
                try:
                    tick_size = Decimal(str(float(tick_str)))
                except (ValueError, TypeError):
                    pass

            security_id = int(row.get("SEM_SMST_SECURITY_ID", 0))
            broker_symbol = row.get("SEM_TRADING_SYMBOL", canonical)
            name = row.get("SEM_CUSTOM_SYMBOL", canonical)
            canonical_exchange = _SEGMENT_TO_EXCHANGE.get(dhan_segment, "NFO")

            instruments.append(Instrument(
                canonical_symbol=canonical,
                exchange=canonical_exchange,
                broker_symbol=broker_symbol,
                instrument_token=security_id,
                tradingsymbol=canonical,
                name=name,
                instrument_type=instrument_type,
                lot_size=lot_size,
                tick_size=tick_size,
                expiry=expiry,
                strike=strike,
                option_type=row.get("SEM_OPTION_TYPE") or None,
                segment=dhan_segment,
            ))

        except Exception as e:
            logger.debug(f"[Dhan] Skipping instrument row: {e}")
            continue

    return instruments


def _row_to_segment(row: dict) -> str:
    """Map CSV row columns to Dhan exchange segment string."""
    exchange = row.get("SEM_EXM_EXCH_ID", "").upper()
    segment = row.get("SEM_SEGMENT", "").upper()

    if exchange == "NSE" and segment == "E":
        return "NSE_EQ"
    elif exchange == "NSE" and segment == "D":
        return "NSE_FNO"
    elif exchange == "BSE" and segment == "E":
        return "BSE_EQ"
    elif exchange == "BSE" and segment == "D":
        return "BSE_FNO"
    elif exchange == "MCX":
        return "MCX_COMM"
    return "NSE_EQ"


_DHAN_INDEX_TO_CANONICAL = {
    "NIFTY": "NIFTY 50",
    "BANKNIFTY": "NIFTY BANK",
    "FINNIFTY": "NIFTY FIN SERVICE",
    "MIDCPNIFTY": "NIFTY MID SELECT",
    "SENSEX": "SENSEX",
    "BANKEX": "BSE-BANKEX",
}


def _row_to_canonical_symbol(row: dict) -> Optional[str]:
    """
    Convert a Dhan CSV row to a canonical symbol (Kite format).

    Dhan trading symbol examples:
        NIFTY-Feb2026-24000-CE -> NIFTY26FEB24000CE
        NIFTY-Feb2026-FUT      -> NIFTY26FEBFUT
        HDFCBANK               -> HDFCBANK (no change)
        NIFTY (INDEX)          -> NIFTY 50
    """
    instrument_name = row.get("SEM_INSTRUMENT_NAME", "")
    trading_symbol = row.get("SEM_TRADING_SYMBOL", "")

    if instrument_name == "INDEX":
        return _DHAN_INDEX_TO_CANONICAL.get(trading_symbol.strip())

    if instrument_name == "EQUITY":
        return trading_symbol.strip()

    elif instrument_name in ("OPTIDX", "OPTSTK"):
        # NIFTY-Feb2026-24000-CE
        parts = trading_symbol.split("-")
        if len(parts) < 4:
            return None
        name = parts[0]
        expiry_code = _format_expiry_to_canonical(row.get("SEM_EXPIRY_DATE", ""))
        if not expiry_code:
            return None
        strike_str = row.get("SEM_STRIKE_PRICE", "")
        try:
            strike = str(int(float(strike_str)))
        except (ValueError, TypeError):
            return None
        opt_type = row.get("SEM_OPTION_TYPE", "")
        if not opt_type:
            return None
        return f"{name}{expiry_code}{strike}{opt_type}"

    elif instrument_name in ("FUTIDX", "FUTSTK"):
        # NIFTY-Feb2026-FUT or NIFTY-Feb2026
        parts = trading_symbol.split("-")
        name = parts[0]
        expiry_code = _format_expiry_to_canonical(row.get("SEM_EXPIRY_DATE", ""))
        if not expiry_code:
            return None
        return f"{name}{expiry_code}FUT"

    return None


def _format_expiry_to_canonical(expiry_str: str) -> Optional[str]:
    """
    Convert Dhan expiry date string to canonical format.

    "2026-02-27" -> "26FEB"
    "2026-02-27 14:30:00" -> "26FEB"
    """
    if not expiry_str or not expiry_str.strip():
        return None
    # Strip to date-only part (handles "2026-05-26 14:30:00" from CSV)
    date_part = expiry_str.strip()[:10]
    try:
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%y%b").upper()  # "26FEB"
    except (ValueError, TypeError):
        return None
