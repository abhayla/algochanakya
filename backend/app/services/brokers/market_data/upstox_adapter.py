"""
Upstox Market Data Adapter

Wraps Upstox REST API v2 for market data operations in the unified
MarketDataBrokerAdapter interface.

Key characteristics:
- Auth: OAuth 2.0 — Authorization: Bearer {access_token}
  extended_token valid ~1 year (read-only, ideal for platform market data)
- All prices in RUPEES natively (no paise conversion needed)
- instrument_key format: "{EXCHANGE_SEGMENT}|{instrument_token}"
  e.g. "NSE_FO|12345", "NSE_INDEX|Nifty 50", "NSE_EQ|2885"
- Historical candles: descending order (newest first) — adapter reverses to ascending
- Historical endpoint: GET /v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
- Quote endpoint: GET /v2/market-quote/quotes?instrument_key=...
- LTP endpoint: GET /v2/market-quote/ltp?instrument_key=...
- Instrument CSV: downloaded from Upstox CDN per exchange
- Rate limits: 25 req/sec

Key responsibilities:
- get_quote via GET /v2/market-quote/quotes (full quote with 5-level depth)
- get_ltp via GET /v2/market-quote/ltp
- get_historical via GET /v2/historical-candle/{key}/{interval}/{to}/{from}
- get_instruments by downloading and parsing Upstox instrument CSV
- Token mapping via TokenManager (canonical <-> instrument_key)
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Callable

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    UpstoxMarketDataCredentials,
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

# Upstox REST API base URL
UPSTOX_API_BASE = "https://api.upstox.com/v2"

# Instrument CSV download URL — one CSV per exchange segment
UPSTOX_INSTRUMENT_CSV_URLS = {
    "NSE_FO": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz",
    "NSE_EQ": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz",
    "NSE_INDEX": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz",
    "BSE_FO": "https://assets.upstox.com/market-quote/instruments/exchange/BSE.csv.gz",
    "BSE_EQ": "https://assets.upstox.com/market-quote/instruments/exchange/BSE.csv.gz",
    "MCX_FO": "https://assets.upstox.com/market-quote/instruments/exchange/MCX.csv.gz",
    # Fallback URL for plain CSV
    "DEFAULT": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv",
}

# Interval mapping: canonical -> Upstox interval string
_INTERVAL_MAP = {
    "1min": "1minute",
    "2min": "2minute",
    "3min": "3minute",
    "5min": "5minute",
    "10min": "10minute",
    "15min": "15minute",
    "20min": "20minute",
    "30min": "30minute",
    "hour": "60minute",
    "1hour": "60minute",
    "60min": "60minute",
    "day": "day",
    "1day": "day",
    "week": "week",
    "month": "month",
}

# Exchange segment mapping
_SEGMENT_TO_EXCHANGE = {
    "NSE_FO": "NFO",
    "NSE_EQ": "NSE",
    "NSE_INDEX": "NSE",
    "BSE_FO": "BFO",
    "BSE_EQ": "BSE",
    "MCX_FO": "MCX",
}

# Instrument type mapping from CSV column
_INSTRUMENT_TYPE_MAP = {
    "OPTIDX": "CE",   # resolved further by option_type column
    "OPTSTK": "CE",
    "FUTIDX": "FUT",
    "FUTSTK": "FUT",
    "EQ": "EQ",
    "INDEX": "INDEX",
}


def _parse_upstox_csv(csv_text: str) -> List[dict]:
    """Parse Upstox instrument CSV and return list of row dicts."""
    lines = csv_text.splitlines()
    if not lines:
        return []

    headers = [h.strip().lower() for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < len(headers):
            parts += [""] * (len(headers) - len(parts))
        row = {headers[i]: parts[i].strip() for i in range(len(headers))}
        rows.append(row)
    return rows


def _upstox_row_to_instrument(row: dict) -> Optional["Instrument"]:
    """
    Convert an Upstox CSV row to an Instrument object.

    CSV columns (typical): instrument_key, exchange_token, tradingsymbol, name,
    last_price, expiry, strike, tick_size, lot_size, instrument_type, option_type, exchange
    """
    instrument_key = row.get("instrument_key", "").strip()
    tradingsymbol = row.get("tradingsymbol", "").strip()
    name = row.get("name", "").strip() or tradingsymbol
    exchange = row.get("exchange", "").strip()
    instrument_type_raw = row.get("instrument_type", "EQ").strip().upper()
    option_type = row.get("option_type", "").strip().upper()

    if not tradingsymbol or not instrument_key:
        return None

    # Determine canonical symbol (tradingsymbol is already in Kite canonical format for F&O)
    canonical = tradingsymbol

    # Determine exchange
    canonical_exchange = _SEGMENT_TO_EXCHANGE.get(exchange, "NSE")

    # Determine instrument type
    if instrument_type_raw in ("OPTIDX", "OPTSTK") and option_type in ("CE", "PE"):
        itype = option_type
    elif instrument_type_raw in ("FUTIDX", "FUTSTK"):
        itype = "FUT"
    elif instrument_type_raw == "INDEX":
        itype = "INDEX"
    else:
        itype = "EQ"

    # Parse expiry
    expiry_date = None
    expiry_str = row.get("expiry", "").strip()
    if expiry_str:
        for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                expiry_date = datetime.strptime(expiry_str, fmt).date()
                break
            except ValueError:
                continue

    # Parse strike
    strike = None
    strike_str = row.get("strike", "").strip()
    if strike_str:
        try:
            strike = Decimal(strike_str)
        except Exception:
            pass

    # Parse lot size
    lot_size = 1
    lot_str = row.get("lot_size", "").strip()
    if lot_str:
        try:
            lot_size = int(lot_str)
        except ValueError:
            pass

    # Parse tick size
    tick_size = Decimal("0.05")
    tick_str = row.get("tick_size", "").strip()
    if tick_str:
        try:
            tick_size = Decimal(tick_str)
        except Exception:
            pass

    # Extract numeric token from instrument_key (e.g., "NSE_FO|12345" → 12345)
    try:
        token_str = instrument_key.split("|")[-1] if "|" in instrument_key else instrument_key
        instrument_token = int(token_str)
    except ValueError:
        instrument_token = 0

    return Instrument(
        canonical_symbol=canonical,
        exchange=canonical_exchange,
        broker_symbol=instrument_key,
        instrument_token=instrument_token,
        tradingsymbol=tradingsymbol,
        name=name,
        instrument_type=itype,
        expiry=expiry_date,
        strike=strike,
        lot_size=lot_size,
        tick_size=tick_size,
    )


class UpstoxMarketDataAdapter(MarketDataBrokerAdapter):
    """
    Upstox REST market data adapter.

    Implements the MarketDataBrokerAdapter interface using Upstox REST APIs v2.
    All prices are returned in RUPEES (no paise conversion needed).
    Uses Bearer token authentication.

    instrument_key format: "{EXCHANGE_SEGMENT}|{numeric_token}"
    e.g. "NSE_FO|12345", "NSE_INDEX|Nifty 50"
    """

    # Map bare index names to Upstox instrument_key format
    INDEX_KEY_MAP = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "NIFTY 50": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank",
        "NIFTY BANK": "NSE_INDEX|Nifty Bank",
        "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
        "NIFTY FIN SERVICE": "NSE_INDEX|Nifty Fin Service",
        "SENSEX": "BSE_INDEX|SENSEX",
    }

    def __init__(self, credentials: UpstoxMarketDataCredentials, db: AsyncSession):
        self._credentials = credentials
        self._db = db
        self._initialized = False
        self._tick_callback: Optional[Callable] = None
        self._token_manager = TokenManagerFactory.get_manager("upstox", db)

        # Bearer token auth header
        self._headers = {
            "Authorization": f"Bearer {credentials.access_token}",
            "Accept": "application/json",
            "Api-Version": "2.0",
        }

    @property
    def broker_type(self) -> str:
        return MarketDataBrokerType.UPSTOX

    @property
    def is_connected(self) -> bool:
        return self._initialized

    async def connect(self, **kwargs) -> bool:
        """
        Connect by verifying credentials against Upstox profile endpoint.
        """
        try:
            await self._token_manager.load_cache()
            await self._make_request("GET", "/user/profile")
            self._initialized = True
            logger.info("[UpstoxAdapter] Connected successfully")
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str or "invalid token" in err_str:
                raise AuthenticationError("upstox", f"Token invalid or expired: {e}")
            logger.warning(f"[UpstoxAdapter] connect() failed (non-auth): {e}")
            return False

    async def disconnect(self) -> None:
        """Mark adapter as disconnected."""
        self._initialized = False
        logger.info("[UpstoxAdapter] Disconnected")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch Last Traded Price for a list of canonical symbols.

        Uses GET /v3/market-quote/ltp (preferred — has 'cp' for previous close).
        Falls back to v2 if v3 fails.
        When market is closed, ltp=0 — returns 'cp' (previous close) instead.
        """
        # Map canonical symbols to instrument_keys
        key_to_canonical: Dict[str, str] = {}
        for sym in symbols:
            index_key = self.INDEX_KEY_MAP.get(sym.upper())
            if index_key:
                key_to_canonical[index_key] = sym
                continue
            instr_key = await self._token_manager.get_token(sym)
            if instr_key is None:
                raise InvalidSymbolError("upstox", sym)
            key_to_canonical[str(instr_key)] = sym

        instrument_keys_param = ",".join(key_to_canonical.keys())

        # Try v3 first — it has 'cp' (previous close) unlike v2
        try:
            resp = await self._make_request(
                "GET", "/v3/market-quote/ltp",
                params={"instrument_key": instrument_keys_param},
                _base_override="https://api.upstox.com",
            )
            result: Dict[str, Decimal] = {}
            for instr_key, item in resp.get("data", {}).items():
                normalized_key = instr_key.replace(":", "|")
                lookup_key = instr_key if instr_key in key_to_canonical else normalized_key
                if lookup_key not in key_to_canonical:
                    continue
                canonical = key_to_canonical[lookup_key]
                last_price = float(item.get("last_price", 0) or 0)
                cp = float(item.get("cp", 0) or 0)  # previous close — always populated
                # Use previous close when ltp is 0 (market closed)
                result[canonical] = Decimal(str(last_price if last_price else cp))
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("upstox", str(e))
            logger.warning(f"[UpstoxAdapter] v3 LTP failed ({e}), falling back to v2")

        # Fallback: v2 (no previous close — returns 0 when market is closed)
        try:
            resp = await self._make_request(
                "GET", "/market-quote/ltp",
                params={"instrument_key": instrument_keys_param}
            )
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("upstox", str(e))
            raise BrokerAPIError("upstox", f"get_ltp failed: {e}")

        result: Dict[str, Decimal] = {}
        for instr_key, item in resp.get("data", {}).items():
            normalized_key = instr_key.replace(":", "|")
            lookup_key = instr_key if instr_key in key_to_canonical else normalized_key
            if lookup_key not in key_to_canonical:
                continue
            canonical = key_to_canonical[lookup_key]
            result[canonical] = Decimal(str(item["last_price"]))
        return result

    async def get_option_chain_quotes(self, underlying: str, expiry_date: str, token_to_symbol: dict = None) -> dict:
        """
        Fetch option chain data from Upstox /v2/option/chain endpoint.

        Returns all_quotes dict in the same format used by optionchain.py:
            {"NFO:<tradingsymbol>": {"last_price", "oi", "volume", "ohlc": {"close", ...}}}

        Key advantage: market_data.close_price is the previous day's close — always
        non-zero even when market is closed (confirmed by Upstox support).
        When ltp=0 (market closed), last_price is set to close_price automatically.

        Args:
            underlying: "NIFTY", "BANKNIFTY", "FINNIFTY"
            expiry_date: "YYYY-MM-DD"
        """
        instrument_key = self.INDEX_KEY_MAP.get(underlying.upper())
        if not instrument_key:
            raise InvalidSymbolError("upstox", underlying)

        try:
            resp = await self._make_request(
                "GET", "/option/chain",
                params={"instrument_key": instrument_key, "expiry_date": expiry_date}
            )
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("upstox", str(e))
            raise BrokerAPIError("upstox", f"get_option_chain_quotes failed: {e}")

        all_quotes: dict = {}
        for entry in resp.get("data", []):
            for side_key in ("call_options", "put_options"):
                opt = entry.get(side_key)
                if not opt:
                    continue

                # Extract token from instrument_key (e.g., "NSE_FO|54771" → "54771")
                instr_key = opt.get("instrument_key", "")
                token = instr_key.split("|")[-1] if "|" in instr_key else ""

                # Map token to canonical symbol via caller-provided mapping
                canonical_symbol = ""
                if token_to_symbol and token:
                    canonical_symbol = token_to_symbol.get(token, "")
                if not canonical_symbol:
                    continue

                md = opt.get("market_data", {})
                ltp = float(md.get("ltp", 0) or 0)
                close_price = float(md.get("close_price", 0) or 0)

                # Extract pre-calculated Greeks from Upstox response
                greeks_data = opt.get("option_greeks", {})

                symbol_key = f"NFO:{canonical_symbol}"
                all_quotes[symbol_key] = {
                    "last_price": ltp if ltp else close_price,  # use close when ltp=0
                    "oi": int(md.get("oi", 0) or 0),
                    "volume": int(md.get("volume", 0) or 0),
                    "ohlc": {
                        "open": float(md.get("open_price", 0) or 0),
                        "high": float(md.get("high_price", 0) or 0),
                        "low": float(md.get("low_price", 0) or 0),
                        "close": close_price,
                    },
                    "depth": {
                        "buy": [{"price": float(md.get("bid_price", 0) or 0), "quantity": int(md.get("bid_qty", 0) or 0)}] if md.get("bid_price") else [],
                        "sell": [{"price": float(md.get("ask_price", 0) or 0), "quantity": int(md.get("ask_qty", 0) or 0)}] if md.get("ask_price") else [],
                    },
                    "greeks": {
                        "iv": float(greeks_data.get("iv", 0) or 0),
                        "delta": float(greeks_data.get("delta", 0) or 0),
                        "gamma": float(greeks_data.get("gamma", 0) or 0),
                        "theta": float(greeks_data.get("theta", 0) or 0),
                        "vega": float(greeks_data.get("vega", 0) or 0),
                    } if greeks_data else None,
                }

        logger.info(f"[UpstoxAdapter] get_option_chain_quotes: {len(all_quotes)} contracts for {underlying} {expiry_date}")
        return all_quotes

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Fetch full quote (OHLC, volume, OI, bid/ask) for canonical symbols.

        Uses GET /v2/market-quote/quotes?instrument_key=NSE_FO|12345,...
        """
        # Map canonical symbols to instrument_keys
        key_to_canonical: Dict[str, str] = {}
        for sym in symbols:
            # Check if it's a bare index name first
            index_key = self.INDEX_KEY_MAP.get(sym.upper())
            if index_key:
                key_to_canonical[index_key] = sym
                continue
            instr_key = await self._token_manager.get_token(sym)
            if instr_key is None:
                raise InvalidSymbolError("upstox", sym)
            key_to_canonical[str(instr_key)] = sym

        instrument_keys_param = ",".join(key_to_canonical.keys())

        try:
            resp = await self._make_request(
                "GET", "/market-quote/quotes",
                params={"instrument_key": instrument_keys_param}
            )
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("upstox", str(e))
            raise BrokerAPIError("upstox", f"get_quote failed: {e}")

        result: Dict[str, UnifiedQuote] = {}
        for instr_key, item in resp.get("data", {}).items():
            # Upstox returns keys with ":" separator but we store with "|"
            normalized_key = instr_key.replace(":", "|")
            lookup_key = instr_key if instr_key in key_to_canonical else normalized_key
            if lookup_key not in key_to_canonical:
                continue
            canonical = key_to_canonical[lookup_key]

            ohlc = item.get("ohlc", {})
            depth = item.get("depth", {})
            buy_depth = depth.get("buy", [{}])
            sell_depth = depth.get("sell", [{}])

            bid_price = Decimal(str(buy_depth[0]["price"])) if buy_depth else Decimal("0")
            ask_price = Decimal(str(sell_depth[0]["price"])) if sell_depth else Decimal("0")
            bid_qty = int(buy_depth[0].get("quantity", 0)) if buy_depth else 0
            ask_qty = int(sell_depth[0].get("quantity", 0)) if sell_depth else 0

            result[canonical] = UnifiedQuote(
                tradingsymbol=canonical,
                last_price=Decimal(str(item.get("last_price", 0))),
                open=Decimal(str(ohlc.get("open", 0))),
                high=Decimal(str(ohlc.get("high", 0))),
                low=Decimal(str(ohlc.get("low", 0))),
                close=Decimal(str(ohlc.get("close", 0))),
                volume=int(item.get("volume") or 0),
                oi=int(item.get("oi") or 0),
                bid_price=bid_price,
                ask_price=ask_price,
                bid_quantity=bid_qty,
                ask_quantity=ask_qty,
            )
        return result

    async def get_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        interval: str,
    ) -> List[OHLCVCandle]:
        """
        Fetch OHLCV candles for a canonical symbol.

        Uses GET /v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
        Note: Upstox returns newest-first; adapter reverses to oldest-first.
        """
        instr_key = await self._token_manager.get_token(symbol)
        if instr_key is None:
            raise InvalidSymbolError("upstox", symbol)

        upstox_interval = _INTERVAL_MAP.get(interval.lower(), "day")

        # URL encode the instrument_key (| must be %7C)
        from urllib.parse import quote as url_quote
        encoded_key = url_quote(str(instr_key), safe="")

        to_str = to_date.strftime("%Y-%m-%d")
        from_str = from_date.strftime("%Y-%m-%d")

        try:
            resp = await self._make_request(
                "GET",
                f"/historical-candle/{encoded_key}/{upstox_interval}/{to_str}/{from_str}",
            )
        except Exception as e:
            raise DataNotAvailableError("upstox", f"{symbol}: {e}")

        candles_raw = resp.get("data", {}).get("candles", [])

        candles = []
        for row in candles_raw:
            # row: [timestamp_str, O, H, L, C, V, OI]
            # timestamp is ISO string like "2026-01-01T09:15:00+05:30"
            ts_raw = row[0]
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw)
            else:
                try:
                    # Handle ISO format with timezone
                    ts = datetime.fromisoformat(str(ts_raw).replace("+05:30", ""))
                except ValueError:
                    ts = datetime.now()

            candles.append(OHLCVCandle(
                timestamp=ts,
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=int(row[5]),
            ))

        # Upstox returns newest first; reverse to oldest first
        candles.reverse()
        return candles

    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Download and parse Upstox instrument CSV.

        Filters by exchange and returns Instrument objects with canonical symbols.
        """
        try:
            csv_text = await self._download_instrument_csv(exchange)
        except Exception as e:
            raise BrokerAPIError("upstox", f"Failed to download instrument CSV: {e}")

        rows = _parse_upstox_csv(csv_text)
        instruments = []
        query_upper = exchange.upper()

        for row in rows:
            exch = row.get("exchange", "").strip().upper()
            canonical_exchange = _SEGMENT_TO_EXCHANGE.get(exch, "NSE")

            # Filter by requested exchange
            if query_upper != "ALL":
                if query_upper in ("NFO", "NSE_FO") and exch != "NSE_FO":
                    continue
                elif query_upper not in ("NFO", "NSE_FO", "ALL") and canonical_exchange != query_upper:
                    continue

            instrument = _upstox_row_to_instrument(row)
            if instrument:
                instruments.append(instrument)

        return instruments

    async def search_instruments(
        self, query: str, exchange: str = "ALL"
    ) -> List[Instrument]:
        """Search instruments by name or symbol (case-insensitive, max 50)."""
        try:
            csv_text = await self._download_instrument_csv(exchange)
        except Exception:
            return []

        rows = _parse_upstox_csv(csv_text)
        query_upper = query.upper()
        results = []

        for row in rows:
            tradingsymbol = row.get("tradingsymbol", "").strip().upper()
            name = row.get("name", "").strip().upper()
            if query_upper in tradingsymbol or query_upper in name:
                instrument = _upstox_row_to_instrument(row)
                if instrument:
                    results.append(instrument)
                    if len(results) >= 50:
                        break

        return results

    async def get_token(self, canonical_symbol: str) -> str:
        """Look up Upstox instrument_key for a canonical symbol."""
        token = await self._token_manager.get_token(canonical_symbol)
        if token is None:
            raise InvalidSymbolError("upstox", canonical_symbol)
        return str(token)

    async def get_symbol(self, token) -> str:
        """Look up canonical symbol for an Upstox instrument_key."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError("upstox", str(token))
        return symbol

    # ─── WebSocket stubs (REST-only adapter) ─────────────────────────────────

    async def subscribe(self, tokens: List, mode: str = "quote") -> None:
        """No-op: use Upstox TickerAdapter (Protobuf WebSocket) for streaming."""
        pass

    async def unsubscribe(self, tokens: List) -> None:
        """No-op: use Upstox TickerAdapter for streaming."""
        pass

    def on_tick(self, callback: Callable) -> None:
        """Register tick callback (no-op for REST adapter)."""
        self._tick_callback = callback

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _make_request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        _base_override: Optional[str] = None,
    ) -> dict:
        """
        Execute an authenticated HTTP request against Upstox API.

        Raises exceptions for HTTP errors; returns parsed JSON dict.
        _base_override replaces UPSTOX_API_BASE for the request (used for v3 paths).
        """
        base = _base_override if _base_override else UPSTOX_API_BASE
        url = f"{base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers,
                json=json,
                params=params,
            )
            if response.status_code == 401:
                raise Exception(f"Unauthorized token 401: {response.text}")
            if response.status_code == 429:
                raise Exception(f"Rate limit exceeded 429: {response.text}")
            response.raise_for_status()
            return response.json()

    async def _download_instrument_csv(self, exchange: str = "NSE") -> str:
        """Download Upstox instrument CSV for the given exchange."""
        # Map exchange to the appropriate URL
        url = UPSTOX_INSTRUMENT_CSV_URLS.get(
            exchange.upper(),
            UPSTOX_INSTRUMENT_CSV_URLS["DEFAULT"]
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()

            # Handle gzip compressed response
            content_type = response.headers.get("content-type", "")
            if "gzip" in content_type or url.endswith(".gz"):
                import gzip
                return gzip.decompress(response.content).decode("utf-8")
            return response.text
