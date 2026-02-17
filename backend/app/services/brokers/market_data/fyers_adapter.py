"""
Fyers Market Data Adapter

Wraps Fyers REST API v3 for market data operations in the unified
MarketDataBrokerAdapter interface.

Key characteristics:
- Exchange-prefixed symbols: NSE:NIFTY26FEB24000CE (strip prefix → canonical)
- All prices in RUPEES natively (no paise conversion needed)
- Auth header: 'Authorization: {app_id}:{access_token}' (colon-separated, NOT Bearer)
- Quotes endpoint: POST /v3/quotes with comma-separated symbols string (max 50)
- Historical endpoint: GET /v3/history with Unix epoch range_from/range_to
- Instrument CSV per segment: public.fyers.in/sym_details/{NSE_FO,NSE_CM,...}.csv
- Historical response: {"candles": [[epoch, O, H, L, C, V], ...]}

Key responsibilities:
- get_quote via POST /api/v3/quotes
- get_ltp extracted from quotes response (same endpoint, lighter field)
- get_historical via GET /api/v3/history
- get_instruments by downloading Fyers segment CSV files
- Token mapping via TokenManager (canonical <-> Fyers Fytoken)
"""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from typing import List, Dict, Optional, Callable

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    FyersMarketDataCredentials,
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

# Fyers REST API base URL (v3)
FYERS_API_BASE = "https://api-t1.fyers.in/api/v3"

# Instrument CSV URLs per segment
FYERS_CSV_URLS = {
    "NFO": "https://public.fyers.in/sym_details/NSE_FO.csv",
    "NSE": "https://public.fyers.in/sym_details/NSE_CM.csv",
    "BFO": "https://public.fyers.in/sym_details/BSE_FO.csv",
    "BSE": "https://public.fyers.in/sym_details/BSE_CM.csv",
    "MCX": "https://public.fyers.in/sym_details/MCX_COM.csv",
}

# Canonical interval -> Fyers resolution string
_INTERVAL_MAP = {
    "1min": "1",
    "2min": "2",
    "3min": "3",
    "5min": "5",
    "10min": "10",
    "15min": "15",
    "30min": "30",
    "hour": "60",
    "2hour": "120",
    "4hour": "240",
    "day": "D",
    "week": "W",
    "month": "M",
}

# Index name mappings: Fyers bare name -> canonical
_INDEX_FYERS_TO_CANONICAL = {
    "NIFTY50": "NIFTY 50",
    "NIFTYBANK": "NIFTY BANK",
    "FINNIFTY": "NIFTY FIN SERVICE",
    "SENSEX": "SENSEX",
    "BANKEX": "BANKEX",
    "INDIAVIX": "INDIA VIX",
    "MIDCPNIFTY": "NIFTY MID SELECT",
}
_INDEX_CANONICAL_TO_FYERS = {v: k for k, v in _INDEX_FYERS_TO_CANONICAL.items()}
_BSE_INDICES = {"SENSEX", "BANKEX"}

# Fyers instrument type -> instrument_type field
_INSTRUMENT_TYPE_MAP = {
    "OI": "CE",   # Options Index - overridden by Option type column
    "OS": "CE",   # Options Stock
    "IF": "FUT",  # Index Future
    "SF": "FUT",  # Stock Future
    "EQ": "EQ",   # Equity
    "II": "EQ",   # Index (non-tradable)
}


class FyersMarketDataAdapter(MarketDataBrokerAdapter):
    """
    Fyers market data adapter for quotes, historical data, and instruments.

    Wraps Fyers REST API v3. All prices in RUPEES (no conversion needed).
    Symbols converted between canonical (Kite) format and Fyers NSE:SYMBOL format.
    """

    def __init__(self, credentials: FyersMarketDataCredentials, db: AsyncSession):
        """
        Initialize Fyers adapter.

        Args:
            credentials: Fyers credentials (app_id, access_token)
            db: Database session for token lookups
        """
        super().__init__(credentials)
        self.db = db
        self._token_manager = TokenManagerFactory.get_manager("fyers", db)
        self._ticker_callbacks: List[Callable] = []

        # Fyers unique auth: "app_id:access_token" (NOT Bearer)
        auth_value = f"{credentials.app_id}:{credentials.access_token}"
        self._headers = {
            "Authorization": auth_value,
            "Content-Type": "application/json",
        }

    @property
    def broker_type(self) -> MarketDataBrokerType:
        return MarketDataBrokerType.FYERS

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for canonical symbols.

        Uses POST /api/v3/quotes with comma-separated Fyers symbols.
        Max 50 symbols per request.

        Args:
            symbols: List of canonical symbols (e.g., NIFTY26FEB24000CE)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote (prices in RUPEES)
        """
        try:
            # Convert canonical -> Fyers format, batch into ≤50
            fyers_symbols = [self._canonical_to_fyers(s) for s in symbols]
            unified_quotes = {}

            for batch_start in range(0, len(fyers_symbols), 50):
                batch = fyers_symbols[batch_start:batch_start + 50]
                body = {"symbols": ",".join(batch)}
                raw = await self._make_request("POST", "/quotes", body=body)

                if raw.get("s") == "error":
                    raise BrokerAPIError("fyers", raw.get("message", "Quotes API error"))

                for item in raw.get("d", []):
                    if item.get("s") != "ok":
                        continue
                    fyers_sym = item.get("n", "")
                    canonical = self._fyers_to_canonical(fyers_sym)
                    v = item.get("v", {})
                    unified_quotes[canonical] = self._convert_to_unified_quote(v, canonical)

            return unified_quotes

        except (AuthenticationError, BrokerAPIError):
            raise
        except Exception as e:
            logger.error(f"[Fyers] get_quote error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("fyers", str(e))
            raise BrokerAPIError("fyers", f"Failed to get quotes: {str(e)}")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP for canonical symbols.

        Reuses the quotes endpoint and extracts only 'lp' (last price).

        Args:
            symbols: List of canonical symbols

        Returns:
            Dict mapping canonical symbol to LTP in RUPEES
        """
        try:
            fyers_symbols = [self._canonical_to_fyers(s) for s in symbols]
            ltp_map = {}

            for batch_start in range(0, len(fyers_symbols), 50):
                batch = fyers_symbols[batch_start:batch_start + 50]
                body = {"symbols": ",".join(batch)}
                raw = await self._make_request("POST", "/quotes", body=body)

                if raw.get("s") == "error":
                    raise BrokerAPIError("fyers", raw.get("message", "Quotes API error"))

                for item in raw.get("d", []):
                    if item.get("s") != "ok":
                        continue
                    fyers_sym = item.get("n", "")
                    canonical = self._fyers_to_canonical(fyers_sym)
                    lp = item.get("v", {}).get("lp", 0)
                    ltp_map[canonical] = Decimal(str(lp))

            return ltp_map

        except (AuthenticationError, BrokerAPIError):
            raise
        except Exception as e:
            logger.error(f"[Fyers] get_ltp error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("fyers", str(e))
            raise BrokerAPIError("fyers", f"Failed to get LTP: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS (delegated to ticker adapter)
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """WebSocket managed separately via FyersTickerAdapter."""
        logger.warning("[Fyers] subscribe() called on REST adapter - WebSocket managed separately")

    async def unsubscribe(self, tokens: List[int]) -> None:
        """WebSocket managed separately via FyersTickerAdapter."""
        logger.warning("[Fyers] unsubscribe() called on REST adapter - WebSocket managed separately")

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
        Get historical OHLCV candles via GET /api/v3/history.

        Fyers response: {"candles": [[epoch, O, H, L, C, V], ...]}
        Prices in RUPEES, timestamps as Unix epoch.

        Args:
            symbol: Canonical symbol (e.g., NIFTY26FEB24000CE, HDFCBANK)
            from_date: Start date
            to_date: End date
            interval: "1min", "5min", "15min", "hour", "day", etc.

        Returns:
            List of OHLCVCandle (prices in RUPEES, Decimal)
        """
        try:
            fyers_symbol = self._canonical_to_fyers(symbol)
            resolution = _INTERVAL_MAP.get(interval, "D")

            # Fyers expects Unix epoch timestamps
            range_from = int(datetime.combine(from_date, datetime.min.time()).timestamp())
            range_to = int(datetime.combine(to_date, datetime.max.time()).timestamp())

            params = {
                "symbol": fyers_symbol,
                "resolution": resolution,
                "range_from": range_from,
                "range_to": range_to,
                "date_format": "0",  # Unix epoch format
            }

            raw = await self._make_request("GET", "/history", params=params)

            if raw.get("s") == "error":
                raise DataNotAvailableError("fyers", raw.get("message", "Historical data error"))

            candles_data = raw.get("candles", [])
            return _parse_candles(candles_data)

        except (DataNotAvailableError, InvalidSymbolError):
            raise
        except Exception as e:
            logger.error(f"[Fyers] get_historical error: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("fyers", str(e))
            raise DataNotAvailableError("fyers", str(e))

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUMENTS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Get instruments by downloading Fyers segment CSV.

        URLs: public.fyers.in/sym_details/{NSE_FO,NSE_CM,BSE_FO,BSE_CM,MCX_COM}.csv

        Args:
            exchange: Canonical exchange code (NFO, NSE, BSE, BFO, MCX)

        Returns:
            List of Instrument objects with canonical symbols
        """
        try:
            csv_url = FYERS_CSV_URLS.get(exchange)
            if not csv_url:
                # Default to NSE F&O
                csv_url = FYERS_CSV_URLS["NFO"]

            csv_content = await self._download_csv(csv_url)
            return _parse_fyers_csv(csv_content, exchange)

        except Exception as e:
            logger.error(f"[Fyers] get_instruments error: {e}")
            raise BrokerAPIError("fyers", f"Failed to get instruments: {str(e)}")

    async def search_instruments(self, query: str) -> List[Instrument]:
        """
        Search instruments by name or symbol.

        Args:
            query: Case-insensitive search query

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
            logger.error(f"[Fyers] search_instruments error: {e}")
            raise BrokerAPIError("fyers", f"Failed to search instruments: {str(e)}")

    async def get_token(self, symbol: str) -> int:
        """Get Fyers Fytoken (as int) for canonical symbol."""
        token = await self._token_manager.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(symbol, "fyers")
        return token

    async def get_symbol(self, token: int) -> str:
        """Get canonical symbol for Fyers Fytoken."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError(f"token:{token}", "fyers")
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
            if profile.get("s") == "error":
                raise AuthenticationError("fyers", profile.get("message", "Auth failed"))

            display_name = profile.get("data", {}).get("display_name", "Unknown")
            logger.info(f"[Fyers] Connected for user: {display_name}")

            await self._token_manager.load_cache()
            self._initialized = True
            logger.info("[Fyers] Adapter initialized successfully")
            return True

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"[Fyers] Failed to connect: {e}")
            if _is_auth_error(e):
                raise AuthenticationError("fyers", str(e))
            return False

    async def disconnect(self) -> None:
        """Close adapter (REST-only, nothing to disconnect)."""
        self._initialized = False
        logger.info("[Fyers] Adapter disconnected")

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
        Make an authenticated request to the Fyers API.

        Auth header: Authorization: {app_id}:{access_token}
        Response envelope: {"s": "ok"|"error", "code": N, ...}
        """
        url = f"{FYERS_API_BASE}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=self._headers, params=params)
            else:
                response = await client.post(url, headers=self._headers, json=body)

            if response.status_code == 401:
                raise AuthenticationError("fyers", "Invalid or expired access token")

            response.raise_for_status()
            return response.json()

    async def _download_csv(self, url: str) -> str:
        """Download a Fyers instrument CSV file."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _canonical_to_fyers(self, canonical: str) -> str:
        """
        Convert canonical symbol to Fyers format.

        Rules:
        - Options/Futures: add NSE: prefix (e.g., NIFTY26FEB24000CE -> NSE:NIFTY26FEB24000CE)
        - Indices: map name + add -INDEX suffix (e.g., NIFTY 50 -> NSE:NIFTY50-INDEX)
        - Equities: add NSE: prefix + -EQ suffix (handled by caller for equity requests)
        """
        # Known index names
        fyers_name = _INDEX_CANONICAL_TO_FYERS.get(canonical)
        if fyers_name:
            exchange = "BSE" if canonical in _BSE_INDICES else "NSE"
            return f"{exchange}:{fyers_name}-INDEX"

        # Options and futures: canonical IS the Fyers symbol (without prefix)
        return f"NSE:{canonical}"

    def _canonical_to_fyers_equity(self, canonical: str) -> str:
        """Convert canonical equity symbol to Fyers format with -EQ suffix."""
        return f"NSE:{canonical}-EQ"

    def _fyers_to_canonical(self, fyers_symbol: str) -> str:
        """
        Convert Fyers symbol to canonical format.

        Rules:
        - NSE:NIFTY26FEB24000CE -> NIFTY26FEB24000CE (strip prefix)
        - NSE:NIFTY50-INDEX -> NIFTY 50 (strip prefix + -INDEX, map name)
        - NSE:HDFCBANK-EQ -> HDFCBANK (strip prefix + -EQ)
        """
        if ":" not in fyers_symbol:
            return fyers_symbol

        _, symbol = fyers_symbol.split(":", 1)

        if symbol.endswith("-INDEX"):
            bare = symbol.replace("-INDEX", "")
            return _INDEX_FYERS_TO_CANONICAL.get(bare, bare)

        if symbol.endswith("-EQ"):
            return symbol.replace("-EQ", "")

        # Derivatives: same as canonical after stripping prefix
        return symbol

    def _convert_to_unified_quote(self, v: dict, canonical_symbol: str) -> UnifiedQuote:
        """
        Convert Fyers quote 'v' dict to UnifiedQuote.

        Fyers field names: lp=last_price, o=open, h=high, l=low, c=close,
        volume=volume, oi=oi, ch=change, chp=change_percent,
        bid/ask = depth arrays
        """
        last_price = Decimal(str(v.get("lp", 0)))
        close_price = Decimal(str(v.get("c", 0)))

        bid_list = v.get("bid", [])
        ask_list = v.get("ask", [])
        best_bid = bid_list[0] if bid_list else {}
        best_ask = ask_list[0] if ask_list else {}

        return UnifiedQuote(
            tradingsymbol=canonical_symbol,
            exchange="NFO",
            instrument_token=None,
            last_price=last_price,
            open=Decimal(str(v.get("o", 0))),
            high=Decimal(str(v.get("h", 0))),
            low=Decimal(str(v.get("l", 0))),
            close=close_price,
            change=Decimal(str(v.get("ch", last_price - close_price))),
            change_percent=Decimal(str(v.get("chp", 0))),
            volume=int(v.get("volume", 0)),
            oi=int(v.get("oi", 0)),
            bid_price=Decimal(str(best_bid.get("price", 0))),
            bid_quantity=int(best_bid.get("quantity", 0)),
            ask_price=Decimal(str(best_ask.get("price", 0))),
            ask_quantity=int(best_ask.get("quantity", 0)),
            last_trade_time=datetime.now(),
            raw_response=v,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _is_auth_error(e: Exception) -> bool:
    """Check if exception is auth-related."""
    msg = str(e).lower()
    return any(kw in msg for kw in ("token", "unauthorized", "401", "-16", "invalid token", "expired"))


def _parse_candles(candles_data: list) -> List[OHLCVCandle]:
    """
    Parse Fyers candle array format into OHLCVCandle list.

    Fyers format: [[epoch, open, high, low, close, volume], ...]
    Prices in RUPEES.
    """
    result = []
    for row in candles_data:
        if len(row) < 6:
            continue
        epoch, o, h, l, c, v = row[0], row[1], row[2], row[3], row[4], row[5]
        try:
            ts = datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
        except (ValueError, TypeError, OSError):
            ts = datetime.now()

        result.append(OHLCVCandle(
            timestamp=ts,
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(l)),
            close=Decimal(str(c)),
            volume=int(v),
            raw_response=None,
        ))
    return result


def _parse_fyers_csv(csv_content: str, exchange: str = "NFO") -> List[Instrument]:
    """
    Parse Fyers instrument CSV into Instrument objects.

    Fyers CSV columns (relevant ones):
    - Fytoken: numeric token (e.g., 101010000043854)
    - Symbol Details: display name
    - Exchange Instrument type: OI/OS/IF/SF/EQ/II
    - Minimum lot size
    - Tick size
    - Expiry date: YYYY-MM-DD
    - Symbol ticker: Fyers symbol (e.g., NSE:NIFTY26FEB24000CE)
    - Exchange: NSE/BSE/MCX
    - Segment: D (derivatives) or C (cash)
    - Strike price: float in RUPEES
    - Option type: CE/PE (blank for non-options)
    """
    import csv as csv_module

    canonical_exchange = exchange
    instruments = []
    reader = csv_module.DictReader(StringIO(csv_content))

    for row in reader:
        try:
            fyers_symbol = row.get("Symbol ticker", "").strip()
            if not fyers_symbol or ":" not in fyers_symbol:
                continue

            instrument_code = row.get("Exchange Instrument type", "").strip()
            option_type = row.get("Option type", "").strip()

            # Determine instrument_type
            instrument_type = _INSTRUMENT_TYPE_MAP.get(instrument_code, "EQ")
            if instrument_code in ("OI", "OS") and option_type:
                instrument_type = option_type  # "CE" or "PE"

            # Convert Fyers symbol to canonical
            canonical = _fyers_sym_to_canonical(fyers_symbol, instrument_type)
            if not canonical:
                continue

            # Parse optional fields
            fytoken_str = row.get("Fytoken", "0").strip()
            try:
                fytoken = int(fytoken_str)
            except (ValueError, TypeError):
                fytoken = 0

            lot_size = 1
            lot_str = row.get("Minimum lot size", "1").strip()
            if lot_str:
                try:
                    lot_size = int(float(lot_str))
                except (ValueError, TypeError):
                    pass

            tick_size = Decimal("0.05")
            tick_str = row.get("Tick size", "0.05").strip()
            if tick_str:
                try:
                    tick_size = Decimal(str(float(tick_str)))
                except (ValueError, TypeError):
                    pass

            expiry = None
            expiry_str = row.get("Expiry date", "").strip()
            if expiry_str:
                try:
                    expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass

            strike = None
            strike_str = row.get("Strike price", "").strip()
            if strike_str and strike_str != "0.0":
                try:
                    strike = Decimal(str(float(strike_str)))
                except (ValueError, TypeError):
                    pass

            name = row.get("Symbol Details", canonical).strip()
            row_exchange = row.get("Exchange", "NSE").strip()

            instruments.append(Instrument(
                canonical_symbol=canonical,
                exchange=canonical_exchange,
                broker_symbol=fyers_symbol,
                instrument_token=fytoken,
                tradingsymbol=canonical,
                name=name,
                instrument_type=instrument_type,
                lot_size=lot_size,
                tick_size=tick_size,
                expiry=expiry,
                strike=strike,
                option_type=option_type or None,
                segment=f"{row_exchange}_{row.get('Segment', 'D')}",
            ))

        except Exception as e:
            logger.debug(f"[Fyers] Skipping instrument row: {e}")
            continue

    return instruments


def _fyers_sym_to_canonical(fyers_symbol: str, instrument_type: str) -> Optional[str]:
    """
    Convert a Fyers symbol string to canonical format.

    NSE:NIFTY26FEB24000CE -> NIFTY26FEB24000CE
    NSE:HDFCBANK-EQ       -> HDFCBANK
    NSE:NIFTY50-INDEX     -> NIFTY 50
    """
    if ":" not in fyers_symbol:
        return None

    _, symbol = fyers_symbol.split(":", 1)

    if symbol.endswith("-INDEX"):
        bare = symbol.replace("-INDEX", "")
        return _INDEX_FYERS_TO_CANONICAL.get(bare, bare)

    if symbol.endswith("-EQ"):
        return symbol.replace("-EQ", "")

    # Derivatives and futures
    return symbol
