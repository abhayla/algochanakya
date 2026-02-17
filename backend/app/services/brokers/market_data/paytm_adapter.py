"""
Paytm Money Market Data Adapter

Wraps Paytm Money REST API for market data operations in the unified
MarketDataBrokerAdapter interface.

Key characteristics:
- 3-token system: access_token (full), public_access_token (WS), read_access_token (read-only REST)
  In AlgoChanakya credentials, access_token is used for all REST reads (acting as read_access_token)
- Auth header: 'x-jwt-token' (NOT Authorization: Bearer)
- All prices in RUPEES natively (no paise conversion needed)
- Quotes via POST /data/v1/price/live (mode LTP or FULL)
- Historical via GET /data/v1/price/ohlc with resolution param
- Instruments via GET /data/v1/scrip/download/csv
- Historical response: {"candles": [[epoch, O, H, L, C, V], ...]}
- Numeric security_id for instruments (string in API payloads)

Key responsibilities:
- get_quote via POST /data/v1/price/live (mode=FULL)
- get_ltp via POST /data/v1/price/live (mode=LTP)
- get_historical via GET /data/v1/price/ohlc
- get_instruments by downloading and parsing Paytm script master CSV
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
    PaytmMarketDataCredentials,
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

# Paytm Money REST API base URL
PAYTM_API_BASE = "https://developer.paytmmoney.com"

# Script master CSV download URL
PAYTM_SCRIPT_MASTER_URL = f"{PAYTM_API_BASE}/data/v1/scrip/download/csv"

# Interval mapping: canonical -> Paytm resolution param
_INTERVAL_MAP = {
    "1min": "1",
    "3min": "3",
    "5min": "5",
    "10min": "10",
    "15min": "15",
    "30min": "30",
    "hour": "60",
    "1hour": "60",
    "60min": "60",
    "day": "1D",
    "1day": "1D",
    "week": "1W",
    "month": "1M",
}

# Segment codes in CSV that map to exchanges
_SEGMENT_TO_EXCHANGE = {
    "D": "NFO",  # Derivatives (F&O)
    "E": "NSE",  # Equity
    "C": "BSE",  # BSE
    "M": "MCX",  # MCX
}

# Month abbreviation map for canonical expiry format
_MONTH_ABBR = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}


def _paytm_sym_to_canonical(row: dict) -> Optional[str]:
    """
    Convert a Paytm script master CSV row to canonical (Kite) symbol format.

    Handles: CE/PE options, FUT futures, equity, indices.
    """
    series = (row.get("series") or "").strip().upper()
    symbol = (row.get("symbol") or "").strip().upper()
    expiry_str = (row.get("expiry") or "").strip()
    option_type = (row.get("option_type") or "").strip().upper()
    strike_str = (row.get("strike_price") or "").strip()

    if series == "INDEX":
        return symbol  # e.g., "NIFTY 50"

    if series == "EQ":
        return symbol  # e.g., "RELIANCE"

    if series in ("OPT", "OPTIDX", "OPTSTK") and option_type in ("CE", "PE") and expiry_str:
        # e.g., NIFTY2522724000CE (weekly) or NIFTY25FEB24000CE (monthly)
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        except ValueError:
            return None
        strike_float = float(strike_str) if strike_str else 0.0
        # Format strike: remove trailing .0 if whole number
        if strike_float == int(strike_float):
            strike_fmt = str(int(strike_float))
        else:
            strike_fmt = str(strike_float)
        year2 = expiry.strftime("%y")
        month = expiry.month
        day = expiry.day
        mon_abbr = _MONTH_ABBR[month]
        # Determine weekly vs monthly (Kite: weekly uses DDMON, monthly uses 3-char month)
        # We use weekly format (yy + day + MON) as Paytm doesn't distinguish
        # For simplicity, use the same format as most current expiries
        return f"{symbol}{year2}{day:02d}{mon_abbr}{strike_fmt}{option_type}"

    if series in ("FUT", "FUTIDX", "FUTSTK") and expiry_str:
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        except ValueError:
            return None
        year2 = expiry.strftime("%y")
        mon_abbr = _MONTH_ABBR[expiry.month]
        return f"{symbol}{year2}{mon_abbr}FUT"

    return None


def _parse_paytm_csv(csv_text: str) -> List[dict]:
    """Parse Paytm script master CSV and return list of row dicts."""
    reader = csv_text.splitlines()
    if not reader:
        return []

    # Parse header
    header_line = reader[0]
    headers = [h.strip().lower() for h in header_line.split(",")]

    rows = []
    for line in reader[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < len(headers):
            parts += [""] * (len(headers) - len(parts))
        row = {headers[i]: parts[i].strip() for i in range(len(headers))}
        rows.append(row)
    return rows


class PaytmMarketDataAdapter(MarketDataBrokerAdapter):
    """
    Paytm Money REST market data adapter.

    Implements the MarketDataBrokerAdapter interface using Paytm Money REST APIs.
    All prices are returned in RUPEES (no paise conversion needed).
    Uses x-jwt-token header for authentication.
    """

    def __init__(self, credentials: PaytmMarketDataCredentials, db: AsyncSession):
        self._credentials = credentials
        self._db = db
        self._initialized = False
        self._tick_callback: Optional[Callable] = None
        self._token_manager = TokenManagerFactory.get_manager("paytm", db)

        # Auth header uses access_token (serves as read_access_token for REST)
        self._headers = {
            "x-jwt-token": credentials.access_token,
            "Content-Type": "application/json",
        }

    @property
    def broker_type(self) -> str:
        return MarketDataBrokerType.PAYTM

    @property
    def is_connected(self) -> bool:
        return self._initialized

    async def connect(self, **kwargs) -> bool:
        """
        Connect by verifying credentials against Paytm profile endpoint.
        """
        try:
            await self._token_manager.load_cache()
            # Verify auth by calling profile endpoint
            await self._make_request("GET", "/accounts/v1/user/details")
            self._initialized = True
            logger.info("[PaytmAdapter] Connected successfully")
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str or "invalid token" in err_str:
                raise AuthenticationError("paytm", f"Token invalid or expired: {e}")
            logger.warning(f"[PaytmAdapter] connect() failed (non-auth): {e}")
            return False

    async def disconnect(self) -> None:
        """Mark adapter as disconnected."""
        self._initialized = False
        logger.info("[PaytmAdapter] Disconnected")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch Last Traded Price for a list of canonical symbols.

        Uses POST /data/v1/price/live with mode=LTP.
        """
        # Map canonical symbols to security_ids
        id_to_canonical: Dict[int, str] = {}
        for sym in symbols:
            sec_id = await self._token_manager.get_token(sym)
            if sec_id is None:
                raise InvalidSymbolError("paytm", sym)
            id_to_canonical[int(sec_id)] = sym

        security_ids = [str(sid) for sid in id_to_canonical.keys()]

        try:
            payload = {
                "mode": "LTP",
                "pref_exchange": "NSE",
                "security_ids": security_ids,
            }
            resp = await self._make_request("POST", "/data/v1/price/live", json=payload)
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("paytm", str(e))
            raise BrokerAPIError("paytm", f"get_ltp failed: {e}")

        result: Dict[str, Decimal] = {}
        for item in resp.get("data", []):
            sec_id = int(item["security_id"])
            if sec_id not in id_to_canonical:
                continue
            canonical = id_to_canonical[sec_id]
            result[canonical] = Decimal(str(item["last_price"]))
        return result

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Fetch full quote (OHLC, volume, OI, bid/ask) for canonical symbols.

        Uses POST /data/v1/price/live with mode=FULL.
        """
        # Map canonical symbols to security_ids
        id_to_canonical: Dict[int, str] = {}
        for sym in symbols:
            sec_id = await self._token_manager.get_token(sym)
            if sec_id is None:
                raise InvalidSymbolError("paytm", sym)
            id_to_canonical[int(sec_id)] = sym

        security_ids = [str(sid) for sid in id_to_canonical.keys()]

        try:
            payload = {
                "mode": "FULL",
                "pref_exchange": "NSE",
                "security_ids": security_ids,
            }
            resp = await self._make_request("POST", "/data/v1/price/live", json=payload)
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                raise AuthenticationError("paytm", str(e))
            raise BrokerAPIError("paytm", f"get_quote failed: {e}")

        result: Dict[str, UnifiedQuote] = {}
        for item in resp.get("data", []):
            sec_id = int(item["security_id"])
            if sec_id not in id_to_canonical:
                continue
            canonical = id_to_canonical[sec_id]
            result[canonical] = UnifiedQuote(
                tradingsymbol=canonical,
                last_price=Decimal(str(item.get("last_price", 0))),
                open=Decimal(str(item.get("open", 0))),
                high=Decimal(str(item.get("high", 0))),
                low=Decimal(str(item.get("low", 0))),
                close=Decimal(str(item.get("close", 0))),
                volume=int(item.get("volume", 0)),
                oi=int(item.get("oi", 0)),
                bid_price=Decimal(str(item.get("bid_price", 0))),
                ask_price=Decimal(str(item.get("ask_price", 0))),
                bid_quantity=int(item.get("bid_qty", 0)),
                ask_quantity=int(item.get("ask_qty", 0)),
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

        Uses GET /data/v1/price/ohlc with resolution param.
        Response format: {"candles": [[epoch, O, H, L, C, V], ...]}
        """
        sec_id = await self._token_manager.get_token(symbol)
        if sec_id is None:
            raise InvalidSymbolError("paytm", symbol)

        resolution = _INTERVAL_MAP.get(interval.lower(), "1D")

        # Convert dates to epoch seconds
        from_epoch = int(datetime.combine(from_date, datetime.min.time()).timestamp())
        to_epoch = int(datetime.combine(to_date, datetime.max.time()).timestamp())

        params = {
            "security_id": str(int(sec_id)),
            "exchange": "NSE",
            "resolution": resolution,
            "from": str(from_epoch),
            "to": str(to_epoch),
        }

        try:
            resp = await self._make_request("GET", "/data/v1/price/ohlc", params=params)
        except Exception as e:
            raise DataNotAvailableError("paytm", f"{symbol}: {e}")

        candles = []
        for row in resp.get("candles", []):
            # row: [epoch, open, high, low, close, volume]
            ts = datetime.fromtimestamp(row[0])
            candles.append(OHLCVCandle(
                timestamp=ts,
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=int(row[5]),
            ))
        return candles

    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Download and parse Paytm script master CSV.

        Filters by exchange/segment and returns Instrument objects with
        canonical symbols.
        """
        try:
            csv_text = await self._download_script_master()
        except Exception as e:
            raise BrokerAPIError("paytm", f"Failed to download script master: {e}")

        rows = _parse_paytm_csv(csv_text)
        instruments = []
        query_upper = exchange.upper()

        for row in rows:
            segment = row.get("segment", "").strip().upper()
            canonical_exchange = _SEGMENT_TO_EXCHANGE.get(segment, "NSE")

            # Filter by requested exchange
            if query_upper not in ("ALL", canonical_exchange, "NFO"):
                # For "NFO" request, include both D (derivatives) rows
                if query_upper == "NFO" and segment != "D":
                    continue
                elif query_upper != canonical_exchange and query_upper != "NFO":
                    continue

            canonical = _paytm_sym_to_canonical(row)
            if not canonical:
                continue

            series = (row.get("series") or "").strip().upper()
            option_type = (row.get("option_type") or "").strip().upper()
            strike_str = (row.get("strike_price") or "").strip()
            expiry_str = (row.get("expiry") or "").strip()
            lot_str = (row.get("lot_size") or "").strip()
            tick_str = (row.get("tick_size") or "").strip()
            security_id = row.get("security_id", "").strip()
            symbol_name = (row.get("symbol") or "").strip().upper()

            # Determine instrument type
            if series in ("OPT", "OPTIDX", "OPTSTK") and option_type in ("CE", "PE"):
                instrument_type = option_type
            elif series in ("FUT", "FUTIDX", "FUTSTK"):
                instrument_type = "FUT"
            elif series == "INDEX":
                instrument_type = "INDEX"
            else:
                instrument_type = "EQ"

            # Parse expiry
            expiry_date = None
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Parse strike
            strike = None
            if strike_str:
                try:
                    strike = Decimal(strike_str)
                except Exception:
                    pass

            # Parse lot size
            lot_size = 1
            if lot_str:
                try:
                    lot_size = int(lot_str)
                except ValueError:
                    pass

            # Parse tick size
            tick_size = None
            if tick_str:
                try:
                    tick_size = Decimal(tick_str)
                except Exception:
                    pass

            try:
                token_int = int(security_id) if security_id else 0
            except ValueError:
                token_int = 0

            instruments.append(Instrument(
                canonical_symbol=canonical,
                exchange=canonical_exchange,
                broker_symbol=security_id,
                instrument_token=token_int,
                tradingsymbol=canonical,
                name=symbol_name,
                instrument_type=instrument_type,
                expiry=expiry_date,
                strike=strike,
                lot_size=lot_size,
                tick_size=tick_size if tick_size is not None else Decimal("0.05"),
            ))

        return instruments

    async def search_instruments(
        self, query: str, exchange: str = "ALL"
    ) -> List[Instrument]:
        """Search instruments by name or symbol (case-insensitive, max 50)."""
        try:
            csv_text = await self._download_script_master()
        except Exception:
            return []

        rows = _parse_paytm_csv(csv_text)
        query_upper = query.upper()
        results = []

        for row in rows:
            symbol_name = (row.get("symbol") or "").strip().upper()
            canonical = _paytm_sym_to_canonical(row)
            if not canonical:
                continue
            if query_upper in symbol_name or query_upper in canonical.upper():
                series = (row.get("series") or "").strip().upper()
                option_type = (row.get("option_type") or "").strip().upper()
                segment = row.get("segment", "").strip().upper()
                canonical_exchange = _SEGMENT_TO_EXCHANGE.get(segment, "NSE")
                security_id = row.get("security_id", "").strip()

                if series in ("OPT", "OPTIDX", "OPTSTK") and option_type in ("CE", "PE"):
                    instrument_type = option_type
                elif series in ("FUT", "FUTIDX", "FUTSTK"):
                    instrument_type = "FUT"
                elif series == "INDEX":
                    instrument_type = "INDEX"
                else:
                    instrument_type = "EQ"

                try:
                    token_int = int(security_id) if security_id else 0
                except ValueError:
                    token_int = 0

                results.append(Instrument(
                    canonical_symbol=canonical,
                    exchange=canonical_exchange,
                    broker_symbol=security_id,
                    instrument_token=token_int,
                    tradingsymbol=canonical,
                    name=symbol_name,
                    instrument_type=instrument_type,
                ))
                if len(results) >= 50:
                    break

        return results

    async def get_token(self, canonical_symbol: str) -> int:
        """Look up Paytm security_id for a canonical symbol."""
        token = await self._token_manager.get_token(canonical_symbol)
        if token is None:
            raise InvalidSymbolError("paytm", canonical_symbol)
        return int(token)

    async def get_symbol(self, token: int) -> str:
        """Look up canonical symbol for a Paytm security_id."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError("paytm", str(token))
        return symbol

    # ─── WebSocket stubs (REST-only adapter) ─────────────────────────────────

    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """No-op: use Paytm WebSocket ticker adapter for streaming."""
        pass

    async def unsubscribe(self, tokens: List[int]) -> None:
        """No-op: use Paytm WebSocket ticker adapter for streaming."""
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
    ) -> dict:
        """
        Execute an authenticated HTTP request against Paytm Money API.

        Raises exceptions for HTTP errors; returns parsed JSON dict.
        """
        url = f"{PAYTM_API_BASE}{path}"
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

    async def _download_script_master(self) -> str:
        """Download Paytm script master CSV text."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                PAYTM_SCRIPT_MASTER_URL,
                headers=self._headers,
            )
            response.raise_for_status()
            return response.text
