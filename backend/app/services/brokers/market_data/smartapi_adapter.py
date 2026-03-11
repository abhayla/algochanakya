"""
SmartAPI Market Data Adapter

Wraps existing SmartAPI services (market_data, historical, instruments, ticker)
in the unified MarketDataBrokerAdapter interface.

Key responsibilities:
- Symbol conversion: SmartAPI format ↔ Canonical (Kite) format
- Price normalization: PAISE (÷100) → RUPEES for WebSocket
- Token mapping via TokenManager
- Error translation to unified exceptions
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    SmartAPIMarketDataCredentials,
    OHLCVCandle,
    Instrument,
)
from app.services.brokers.base import UnifiedQuote
from app.services.brokers.market_data.symbol_converter import SymbolConverter
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    BrokerAPIError,
    InvalidSymbolError,
    DataNotAvailableError,
)
from app.services.brokers.market_data.token_manager import TokenManagerFactory
from app.services.legacy.smartapi_market_data import SmartAPIMarketData, SmartAPIMarketDataError
from app.services.legacy.smartapi_historical import SmartAPIHistorical, SmartAPIHistoricalError
from app.services.legacy.smartapi_instruments import get_smartapi_instruments
from app.config import settings

logger = logging.getLogger(__name__)


class SmartAPIMarketDataAdapter(MarketDataBrokerAdapter):
    """
    SmartAPI adapter for market data operations.

    Wraps SmartAPI REST APIs and WebSocket ticker service.
    """

    def __init__(self, credentials: SmartAPIMarketDataCredentials, db: AsyncSession):
        """
        Initialize SmartAPI adapter.

        Args:
            credentials: SmartAPI credentials (client_id, jwt_token, feed_token)
            db: Database session for token lookups
        """
        super().__init__(credentials)
        self.db = db
        self._symbol_converter = SymbolConverter()
        self._token_manager = TokenManagerFactory.get_manager("smartapi", db)

        # Initialize SmartAPI services with API key from settings
        api_key = getattr(settings, 'ANGEL_API_KEY', None)
        if not api_key:
            raise AuthenticationError(
                "smartapi",
                "ANGEL_API_KEY not configured in settings. Check backend/.env"
            )

        self._market_data = SmartAPIMarketData(
            api_key=api_key,
            jwt_token=credentials.jwt_token
        )
        # Historical data uses a separate API key (ANGEL_HIST_API_KEY).
        # The JWT is BOUND to the key used for login — passing credentials.jwt_token
        # (which was generated with ANGEL_API_KEY) to an instance using ANGEL_HIST_API_KEY
        # causes AG8001. When the keys differ, pass jwt_token=None so SmartAPIHistorical
        # performs its own fresh login with the hist key.
        hist_api_key = getattr(settings, 'ANGEL_HIST_API_KEY', None) or api_key
        hist_jwt = credentials.jwt_token if hist_api_key == api_key else None
        self._historical = SmartAPIHistorical(
            api_key=hist_api_key,
            jwt_token=hist_jwt
        )
        self._instruments = get_smartapi_instruments()  # Use singleton for 12-hour cache

        # WebSocket ticker (managed separately via TickerService)
        self._ticker_callbacks: List[Callable[[List[UnifiedQuote]], None]] = []

    @property
    def broker_type(self) -> MarketDataBrokerType:
        """Return broker type."""
        return MarketDataBrokerType.SMARTAPI

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    # Index names that should use get_index_quote instead of token lookup
    INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "NIFTY 50", "NIFTY BANK"}

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for canonical symbols.

        Args:
            symbols: List of canonical symbols (e.g., NIFTY25APR25000CE) or index names

        Returns:
            Dict mapping canonical symbol to UnifiedQuote
        """
        try:
            unified_quotes = {}
            option_symbols = []

            # Separate indices from options
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper in self.INDEX_SYMBOLS:
                    # Handle index symbols directly via get_index_quote
                    # No token manager or instrument master needed for indices
                    try:
                        index_quote = await self._market_data.get_index_quote(symbol_upper)
                        # Convert to UnifiedQuote (REST API returns prices in RUPEES)
                        unified_quotes[symbol] = self._convert_index_to_unified_quote(
                            index_quote, symbol
                        )
                        logger.info(f"[SmartAPI] Index {symbol} quote fetched")
                    except SmartAPIMarketDataError as e:
                        logger.error(f"[SmartAPI] Failed to get index quote for {symbol}: {e}")
                        raise BrokerAPIError("smartapi", f"Failed to get index quote for {symbol}: {str(e)}")
                else:
                    option_symbols.append(symbol)

            # Handle option symbols via token manager (requires instrument master)
            if option_symbols:
                # Lazy-load instrument master only when needed for options
                if not self._instruments._instruments:
                    logger.info("[SmartAPI] Lazy-loading instrument master for option symbols")
                    await self._instruments.download_master()

                # Pre-load all tokens in ONE bulk DB query instead of N sequential queries.
                # load_cache() is idempotent — safe to call on every get_quote() invocation.
                # Without this, each get_token() cache-miss fires a separate DB round-trip,
                # causing 126+ sequential queries = 7+ second latency → Axios timeout.
                await self._token_manager.load_cache()

                tokens_map = {}  # smartapi_token -> canonical_symbol
                for symbol in option_symbols:
                    token = await self._token_manager.get_token(symbol)
                    if not token:
                        # Fallback: direct lookup via SmartAPI instrument master
                        token_str = await self._instruments.lookup_token(symbol, "NFO")
                        if token_str:
                            token = int(token_str)
                    if token:
                        tokens_map[str(token)] = symbol
                    else:
                        logger.warning(f"[SmartAPI] Token not found for symbol: {symbol}")

                if tokens_map:
                    # Get quotes from SmartAPI (assuming NFO exchange for options)
                    raw_quotes = await self._market_data.get_quote(
                        exchange="NFO",
                        tokens=list(tokens_map.keys()),
                        mode="FULL"
                    )

                    # Convert to UnifiedQuote
                    for token, raw_data in raw_quotes.items():
                        canonical_symbol = tokens_map.get(token)
                        if canonical_symbol:
                            unified_quotes[canonical_symbol] = self._convert_to_unified_quote(
                                raw_data,
                                canonical_symbol
                            )

            return unified_quotes

        except BrokerAPIError:
            raise
        except SmartAPIMarketDataError as e:
            raise BrokerAPIError("smartapi", str(e))
        except Exception as e:
            logger.error(f"[SmartAPI] get_quote error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to get quotes: {str(e)}")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only (lightweight).

        Args:
            symbols: List of canonical symbols or index names (NIFTY, BANKNIFTY, etc.)

        Returns:
            Dict mapping symbol to LTP in RUPEES
        """
        try:
            ltp_map = {}
            option_symbols = []

            # Separate indices from options
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper in self.INDEX_SYMBOLS:
                    # Handle index symbols directly via get_index_quote
                    try:
                        index_quote = await self._market_data.get_index_quote(symbol_upper)
                        # REST API returns prices in RUPEES (already normalized)
                        ltp = index_quote.get("ltp", 0)
                        ltp_map[symbol] = Decimal(str(ltp)) if not isinstance(ltp, Decimal) else ltp
                        logger.info(f"[SmartAPI] Index {symbol} LTP: {ltp}")
                    except SmartAPIMarketDataError as e:
                        logger.error(f"[SmartAPI] Failed to get index quote for {symbol}: {e}")
                        raise BrokerAPIError("smartapi", f"Failed to get index LTP for {symbol}: {str(e)}")
                else:
                    option_symbols.append(symbol)

            # Handle option symbols via token manager (requires instrument master)
            if option_symbols:
                # Lazy-load instrument master only when needed for options
                if not self._instruments._instruments:
                    logger.info("[SmartAPI] Lazy-loading instrument master for option symbols")
                    await self._instruments.download_master()

                # Pre-load all tokens in ONE bulk DB query (same fix as get_quote above).
                await self._token_manager.load_cache()

                tokens_map = {}
                for symbol in option_symbols:
                    token = await self._token_manager.get_token(symbol)
                    if token:
                        tokens_map[str(token)] = symbol

                if tokens_map:
                    # Get LTP quotes for options
                    raw_quotes = await self._market_data.get_quote(
                        exchange="NFO",
                        tokens=list(tokens_map.keys()),
                        mode="LTP"
                    )

                    # Extract LTP (REST API returns prices in RUPEES, already normalized)
                    for token, raw_data in raw_quotes.items():
                        canonical_symbol = tokens_map.get(token)
                        if canonical_symbol:
                            ltp = raw_data.get("ltp", 0)
                            ltp_map[canonical_symbol] = Decimal(str(ltp)) if not isinstance(ltp, Decimal) else ltp

            return ltp_map

        except SmartAPIMarketDataError as e:
            raise BrokerAPIError("smartapi", str(e))
        except Exception as e:
            logger.error(f"[SmartAPI] get_ltp error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to get LTP: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to live ticks via WebSocket.

        Note: WebSocket is managed by the ticker system (TickerPool + TickerRouter).
        Use SmartAPITickerAdapter from app.services.brokers.market_data.ticker.adapters.smartapi.

        Args:
            tokens: List of SmartAPI tokens
            mode: "ltp" or "quote"
        """
        logger.warning("[SmartAPI] subscribe() called on REST adapter - use TickerPool instead")

    async def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from live ticks. Use TickerPool instead."""
        logger.warning("[SmartAPI] unsubscribe() called on REST adapter - use TickerPool instead")

    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """Register callback for incoming ticks."""
        self._ticker_callbacks.append(callback)

    # ═══════════════════════════════════════════════════════════════════════
    # HISTORICAL DATA
    # ═══════════════════════════════════════════════════════════════════════

    # Map SmartAPI bare index names to SmartAPI token + exchange for historical calls
    _INDEX_HISTORICAL_MAP = {
        "NIFTY":            {"exchange": "NSE", "token": "99926000"},
        "NIFTY 50":         {"exchange": "NSE", "token": "99926000"},
        "NIFTY BANK":       {"exchange": "NSE", "token": "99926009"},
        "BANKNIFTY":        {"exchange": "NSE", "token": "99926009"},
        "NIFTY FIN SERVICE":{"exchange": "NSE", "token": "99926037"},
        "FINNIFTY":         {"exchange": "NSE", "token": "99926037"},
        "SENSEX":           {"exchange": "BSE", "token": "99919000"},
    }

    async def get_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        interval: str = "day"
    ) -> List[OHLCVCandle]:
        """
        Get historical OHLCV data.

        Args:
            symbol: Canonical symbol (Kite format) or bare index name
            from_date: Start date
            to_date: End date
            interval: "1min", "5min", "15min", "hour", "day"

        Returns:
            List of OHLCV candles (prices in RUPEES)
        """
        try:
            # Map interval to SmartAPI format
            interval_map = {
                "1min": "ONE_MINUTE",
                "5min": "FIVE_MINUTE",
                "15min": "FIFTEEN_MINUTE",
                "hour": "ONE_HOUR",
                "day": "ONE_DAY",
            }
            smartapi_interval = interval_map.get(interval, "ONE_DAY")

            # Check if symbol is a well-known index (handle without DB lookup)
            index_info = self._INDEX_HISTORICAL_MAP.get(symbol.upper())
            if index_info:
                token = index_info["token"]
                exchange = index_info["exchange"]
            else:
                # Convert canonical symbol to SmartAPI token via token manager
                token = await self._token_manager.get_token(symbol)
                if not token:
                    raise InvalidSymbolError(symbol, "smartapi")
                token = str(token)
                exchange = "NFO"  # Non-index symbols are on NFO

            # Get historical data from SmartAPI
            # get_candles() expects date strings in "YYYY-MM-DD HH:MM" format
            from_date_str = from_date.strftime("%Y-%m-%d 09:15")
            to_date_str = to_date.strftime("%Y-%m-%d 15:30")
            candles_data = await self._historical.get_candles(
                exchange=exchange,
                symbol_token=token,
                interval=smartapi_interval,
                from_date=from_date_str,
                to_date=to_date_str,
            )

            # Convert to OHLCVCandle
            # REST historical API returns prices in RUPEES (not paise) for indices
            # and in PAISE for NFO instruments — check exchange
            paise_divisor = Decimal("100") if exchange == "NFO" else Decimal("1")
            candles = []
            for candle in candles_data:
                candles.append(OHLCVCandle(
                    timestamp=datetime.fromisoformat(candle["timestamp"]),
                    open=Decimal(str(candle["open"])) / paise_divisor,
                    high=Decimal(str(candle["high"])) / paise_divisor,
                    low=Decimal(str(candle["low"])) / paise_divisor,
                    close=Decimal(str(candle["close"])) / paise_divisor,
                    volume=candle["volume"],
                    oi=candle.get("oi"),
                    raw_response=candle
                ))

            return candles

        except SmartAPIHistoricalError as e:
            raise DataNotAvailableError("smartapi", str(e))
        except InvalidSymbolError:
            raise
        except Exception as e:
            logger.error(f"[SmartAPI] get_historical error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to get historical data: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUMENTS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Get all instruments for exchange.

        Args:
            exchange: Exchange code (NSE, NFO, BSE, BFO, MCX)

        Returns:
            List of Instrument objects
        """
        try:
            # Download instrument master if needed
            await self._instruments.download_master()

            # Get all instruments for exchange
            raw_instruments = self._instruments._instruments  # Access internal cache
            filtered = [inst for inst in raw_instruments if inst.get("exch_seg") == exchange]

            # Convert to Instrument objects
            instruments = []
            for raw_inst in filtered:
                try:
                    # Convert SmartAPI symbol to canonical
                    smartapi_symbol = raw_inst.get("symbol", "")
                    canonical_symbol = self._symbol_converter.to_canonical(smartapi_symbol, "smartapi")

                    # Parse expiry from SmartAPI format (e.g., "27JAN2026") to date
                    raw_expiry = raw_inst.get("expiry", "")
                    expiry_date = None
                    if raw_expiry:
                        normalized_expiry = self._instruments._normalize_expiry(raw_expiry)
                        if normalized_expiry:
                            try:
                                expiry_date = datetime.strptime(normalized_expiry, "%Y-%m-%d").date()
                            except ValueError:
                                pass

                    # Parse strike to Decimal (SmartAPI stores in paise, divide by 100)
                    raw_strike = raw_inst.get("strike", "")
                    strike_decimal = None
                    if raw_strike:
                        try:
                            strike_paise = float(raw_strike)
                            strike_rupees = int(strike_paise / 100)  # Convert paise to rupees
                            strike_decimal = Decimal(str(strike_rupees))
                        except:
                            pass

                    # Get instrument type and option type
                    # SmartAPI uses instrumenttype=OPTIDX/OPTSTK, option type (CE/PE) is at end of symbol
                    inst_type = raw_inst.get("instrumenttype", "")
                    option_type = None
                    if smartapi_symbol.endswith("CE"):
                        option_type = "CE"
                    elif smartapi_symbol.endswith("PE"):
                        option_type = "PE"

                    instruments.append(Instrument(
                        canonical_symbol=canonical_symbol,
                        exchange=exchange,
                        broker_symbol=smartapi_symbol,
                        instrument_token=int(raw_inst.get("token") or 0),
                        tradingsymbol=raw_inst.get("name", ""),
                        name=raw_inst.get("name", ""),
                        instrument_type=inst_type,
                        lot_size=int(raw_inst.get("lotsize") or 1),
                        underlying=raw_inst.get("name", ""),  # SmartAPI uses 'name' for underlying
                        expiry=expiry_date,
                        strike=strike_decimal,
                        option_type=option_type,
                    ))
                except Exception as e:
                    # Skip instruments that fail conversion - use WARNING for visibility
                    logger.warning(f"[SmartAPI] Skipping instrument {raw_inst.get('symbol', 'unknown')}: {e}")
                    continue

            return instruments

        except Exception as e:
            logger.error(f"[SmartAPI] get_instruments error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to get instruments: {str(e)}")

    async def search_instruments(self, query: str) -> List[Instrument]:
        """
        Search instruments by name/symbol.

        Args:
            query: Search query (e.g., "NIFTY", "25000 CE")

        Returns:
            List of matching instruments
        """
        try:
            all_instruments = await self.get_instruments("NFO")
            query_lower = query.lower()

            # Simple text search in name and symbol
            matches = [
                inst for inst in all_instruments
                if query_lower in inst.name.lower() or query_lower in inst.canonical_symbol.lower()
            ]

            return matches[:50]  # Limit to 50 results

        except Exception as e:
            logger.error(f"[SmartAPI] search_instruments error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to search instruments: {str(e)}")

    async def get_token(self, symbol: str) -> int:
        """Get SmartAPI token for canonical symbol."""
        token = await self._token_manager.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(symbol, "smartapi")
        return token

    async def get_symbol(self, token: int) -> str:
        """Get canonical symbol for SmartAPI token."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError(f"token:{token}", "smartapi")
        return symbol

    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self, skip_instrument_download: bool = False) -> bool:
        """
        Establish connection (load token cache).

        Args:
            skip_instrument_download: If True, skip downloading instrument master.
                                     Useful for simple queries (index quotes).

        Returns:
            True if successful
        """
        try:
            # Load token cache for fast lookups (lightweight DB query)
            await self._token_manager.load_cache()

            # Download instrument master if needed (can be slow, ~50MB file)
            # Skip for simple queries like index quotes
            if not skip_instrument_download:
                await self._instruments.download_master()

            self._initialized = True
            logger.info("[SmartAPI] Adapter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[SmartAPI] Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection gracefully."""
        # Nothing to disconnect for REST API
        logger.info("[SmartAPI] Adapter disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._initialized

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def _convert_to_unified_quote(self, raw_data: dict, canonical_symbol: str) -> UnifiedQuote:
        """
        Convert SmartAPI quote to UnifiedQuote.

        Args:
            raw_data: Raw quote from SmartAPI
            canonical_symbol: Canonical symbol for this quote

        Returns:
            UnifiedQuote with prices in RUPEES
        """
        # SmartAPI returns prices in PAISE - divide by 100
        ltp = Decimal(str(raw_data.get("ltp", 0))) / 100
        open_price = Decimal(str(raw_data.get("open", 0))) / 100
        high = Decimal(str(raw_data.get("high", 0))) / 100
        low = Decimal(str(raw_data.get("low", 0))) / 100
        close = Decimal(str(raw_data.get("close", 0))) / 100

        return UnifiedQuote(
            tradingsymbol=canonical_symbol,
            exchange=raw_data.get("exchange", "NFO"),
            instrument_token=raw_data.get("token"),
            last_price=ltp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            change=ltp - close if close > 0 else Decimal("0"),
            change_percent=((ltp - close) / close * 100) if close > 0 else Decimal("0"),
            volume=raw_data.get("volume", 0),
            oi=raw_data.get("oi", 0),
            bid_price=Decimal(str(raw_data.get("bid_price", 0))) / 100,
            bid_quantity=raw_data.get("bid_qty", 0),
            ask_price=Decimal(str(raw_data.get("ask_price", 0))) / 100,
            ask_quantity=raw_data.get("ask_qty", 0),
            last_trade_time=datetime.now(),  # SmartAPI doesn't provide this
            raw_response=raw_data
        )

    def _convert_index_to_unified_quote(self, raw_data: dict, symbol: str) -> UnifiedQuote:
        """
        Convert SmartAPI index quote to UnifiedQuote.

        Args:
            raw_data: Raw index quote from SmartAPI (prices in RUPEES, not PAISE)
            symbol: Index symbol (NIFTY 50, NIFTY BANK, etc.)

        Returns:
            UnifiedQuote with prices in RUPEES
        """
        # REST API returns prices in RUPEES for indices (not PAISE)
        ltp = Decimal(str(raw_data.get("ltp", 0)))
        open_price = Decimal(str(raw_data.get("open", 0)))
        high = Decimal(str(raw_data.get("high", 0)))
        low = Decimal(str(raw_data.get("low", 0)))
        close = Decimal(str(raw_data.get("close", 0)))

        return UnifiedQuote(
            tradingsymbol=symbol,
            exchange=raw_data.get("exchange", "NSE"),
            instrument_token=raw_data.get("token"),
            last_price=ltp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            change=ltp - close if close > 0 else Decimal("0"),
            change_percent=((ltp - close) / close * 100) if close > 0 else Decimal("0"),
            volume=raw_data.get("volume", 0),
            oi=raw_data.get("oi", 0),
            bid_price=Decimal("0"),
            bid_quantity=0,
            ask_price=Decimal("0"),
            ask_quantity=0,
            last_trade_time=datetime.now(),
            raw_response=raw_data
        )
