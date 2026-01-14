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
    BrokerAPIError,
    InvalidSymbolError,
    DataNotAvailableError,
)
from app.services.brokers.market_data.token_manager import TokenManagerFactory
from app.services.smartapi_market_data import SmartAPIMarketData, SmartAPIMarketDataError
from app.services.smartapi_historical import SmartAPIHistorical, SmartAPIHistoricalError
from app.services.smartapi_instruments import SmartAPIInstruments

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

        # Initialize SmartAPI services
        self._market_data = SmartAPIMarketData(
            api_key=credentials.broker_type,  # Using broker_type as api_key placeholder
            jwt_token=credentials.jwt_token
        )
        self._historical = SmartAPIHistorical(
            api_key=credentials.broker_type,
            jwt_token=credentials.jwt_token
        )
        self._instruments = SmartAPIInstruments()

        # WebSocket ticker (managed separately via TickerService)
        self._ticker_callbacks: List[Callable[[List[UnifiedQuote]], None]] = []

    @property
    def broker_type(self) -> MarketDataBrokerType:
        """Return broker type."""
        return MarketDataBrokerType.SMARTAPI

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for canonical symbols.

        Args:
            symbols: List of canonical symbols (e.g., NIFTY25APR25000CE)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote
        """
        try:
            # Convert canonical symbols to SmartAPI tokens
            tokens_map = {}  # smartapi_token -> canonical_symbol
            for symbol in symbols:
                token = await self._token_manager.get_token(symbol)
                if token:
                    tokens_map[str(token)] = symbol
                else:
                    logger.warning(f"[SmartAPI] Token not found for symbol: {symbol}")

            if not tokens_map:
                return {}

            # Get quotes from SmartAPI (assuming NFO exchange for options)
            # TODO: Detect exchange from symbol
            raw_quotes = await self._market_data.get_quote(
                exchange="NFO",
                tokens=list(tokens_map.keys()),
                mode="FULL"
            )

            # Convert to UnifiedQuote
            unified_quotes = {}
            for token, raw_data in raw_quotes.items():
                canonical_symbol = tokens_map.get(token)
                if canonical_symbol:
                    unified_quotes[canonical_symbol] = self._convert_to_unified_quote(
                        raw_data,
                        canonical_symbol
                    )

            return unified_quotes

        except SmartAPIMarketDataError as e:
            raise BrokerAPIError("smartapi", str(e))
        except Exception as e:
            logger.error(f"[SmartAPI] get_quote error: {e}")
            raise BrokerAPIError("smartapi", f"Failed to get quotes: {str(e)}")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only (lightweight).

        Args:
            symbols: List of canonical symbols

        Returns:
            Dict mapping canonical symbol to LTP in RUPEES
        """
        try:
            # Convert canonical symbols to SmartAPI tokens
            tokens_map = {}
            for symbol in symbols:
                token = await self._token_manager.get_token(symbol)
                if token:
                    tokens_map[str(token)] = symbol

            if not tokens_map:
                return {}

            # Get LTP quotes
            raw_quotes = await self._market_data.get_quote(
                exchange="NFO",
                tokens=list(tokens_map.keys()),
                mode="LTP"
            )

            # Extract LTP and convert PAISE to RUPEES
            ltp_map = {}
            for token, raw_data in raw_quotes.items():
                canonical_symbol = tokens_map.get(token)
                if canonical_symbol:
                    # SmartAPI returns prices in PAISE for REST API too
                    ltp = raw_data.get("ltp", 0) / 100
                    ltp_map[canonical_symbol] = Decimal(str(ltp))

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

        Note: WebSocket is managed separately via SmartAPITickerService.
        This method is a placeholder for future WebSocket integration.

        Args:
            tokens: List of SmartAPI tokens
            mode: "ltp" or "quote"
        """
        logger.warning("[SmartAPI] subscribe() called on adapter - WebSocket managed separately")
        # TODO: Integrate with SmartAPITickerService

    async def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from live ticks."""
        logger.warning("[SmartAPI] unsubscribe() called on adapter - WebSocket managed separately")
        # TODO: Integrate with SmartAPITickerService

    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
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
        Get historical OHLCV data.

        Args:
            symbol: Canonical symbol (Kite format)
            from_date: Start date
            to_date: End date
            interval: "1min", "5min", "15min", "hour", "day"

        Returns:
            List of OHLCV candles (prices in RUPEES)
        """
        try:
            # Convert canonical symbol to SmartAPI token
            token = await self._token_manager.get_token(symbol)
            if not token:
                raise InvalidSymbolError(symbol, "smartapi")

            # Map interval to SmartAPI format
            interval_map = {
                "1min": "ONE_MINUTE",
                "5min": "FIVE_MINUTE",
                "15min": "FIFTEEN_MINUTE",
                "hour": "ONE_HOUR",
                "day": "ONE_DAY",
            }
            smartapi_interval = interval_map.get(interval, "ONE_DAY")

            # Get historical data from SmartAPI
            candles_data = await self._historical.get_historical(
                token=str(token),
                exchange="NFO",  # TODO: Detect from symbol
                from_date=from_date,
                to_date=to_date,
                interval=smartapi_interval
            )

            # Convert to OHLCVCandle
            candles = []
            for candle in candles_data:
                candles.append(OHLCVCandle(
                    timestamp=datetime.fromisoformat(candle["timestamp"]),
                    open=Decimal(str(candle["open"])) / 100,  # PAISE to RUPEES
                    high=Decimal(str(candle["high"])) / 100,
                    low=Decimal(str(candle["low"])) / 100,
                    close=Decimal(str(candle["close"])) / 100,
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

                    instruments.append(Instrument(
                        canonical_symbol=canonical_symbol,
                        exchange=exchange,
                        broker_symbol=smartapi_symbol,
                        instrument_token=int(raw_inst.get("token", 0)),
                        tradingsymbol=raw_inst.get("name", ""),
                        name=raw_inst.get("name", ""),
                        instrument_type=raw_inst.get("instrumenttype", ""),
                        lot_size=int(raw_inst.get("lotsize", 1)),
                    ))
                except Exception as e:
                    # Skip instruments that fail conversion
                    logger.debug(f"[SmartAPI] Skipping instrument: {e}")
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

    async def connect(self) -> bool:
        """
        Establish connection (load token cache).

        Returns:
            True if successful
        """
        try:
            # Load token cache for fast lookups
            await self._token_manager.load_cache()

            # Download instrument master if needed
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
