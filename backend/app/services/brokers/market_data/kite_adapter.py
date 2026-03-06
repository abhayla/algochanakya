"""
Kite Market Data Adapter

Wraps Kite Connect API for market data operations in the unified
MarketDataBrokerAdapter interface.

Key advantages:
- Symbols are ALREADY in canonical format (Kite format is canonical)
- NO symbol conversion needed
- Prices are in RUPEES (no conversion needed)
- Direct KiteConnect API usage

Key responsibilities:
- Provide quotes via KiteConnect.quote()
- Provide historical data via KiteConnect.historical_data()
- Provide instruments via KiteConnect.instruments()
- Token mapping via TokenManager
- Error translation to unified exceptions
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Dict, Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    KiteMarketDataCredentials,
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
from app.config import settings

logger = logging.getLogger(__name__)


class KiteMarketDataAdapter(MarketDataBrokerAdapter):
    """
    Kite Connect adapter for market data operations.

    Wraps KiteConnect REST APIs for quotes, historical data, and instruments.
    Symbols are already in canonical format - NO conversion needed!
    """

    def __init__(self, credentials: KiteMarketDataCredentials, db: AsyncSession):
        """
        Initialize Kite adapter.

        Args:
            credentials: Kite credentials (access_token)
            db: Database session for token lookups
        """
        super().__init__(credentials)
        self.db = db
        self._token_manager = TokenManagerFactory.get_manager("kite", db)

        # Initialize KiteConnect
        self.kite = KiteConnect(api_key=settings.KITE_API_KEY)
        self.kite.set_access_token(credentials.access_token)

        # WebSocket ticker (managed separately via KiteTickerService)
        self._ticker_callbacks: List[Callable[[List[UnifiedQuote]], None]] = []

    @property
    def broker_type(self) -> MarketDataBrokerType:
        """Return broker type."""
        return MarketDataBrokerType.KITE

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for canonical symbols.

        Args:
            symbols: List of canonical symbols (e.g., NIFTY25APR25000CE)
                    Note: Symbols are ALREADY in Kite format (canonical)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote
        """
        try:
            # Symbols are already in canonical format for Kite!
            # Format: "EXCHANGE:SYMBOL" for API call
            instruments = [f"NFO:{symbol}" for symbol in symbols]

            # Get quotes from Kite
            raw_quotes = self.kite.quote(instruments)

            # Convert to UnifiedQuote
            unified_quotes = {}
            for instrument_key, raw_data in raw_quotes.items():
                # Extract symbol from "NFO:SYMBOL" format
                symbol = instrument_key.split(":")[-1]
                unified_quotes[symbol] = self._convert_to_unified_quote(
                    raw_data,
                    symbol
                )

            return unified_quotes

        except Exception as e:
            logger.error(f"[Kite] get_quote error: {e}")
            # Check if authentication error
            if "token" in str(e).lower() or "session" in str(e).lower():
                raise AuthenticationError("kite", str(e))
            raise BrokerAPIError("kite", f"Failed to get quotes: {str(e)}")

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only (lightweight).

        Args:
            symbols: List of canonical symbols (already in Kite format)

        Returns:
            Dict mapping canonical symbol to LTP in RUPEES
        """
        try:
            # Format: "EXCHANGE:SYMBOL" for API call
            instruments = [f"NFO:{symbol}" for symbol in symbols]

            # Get LTP quotes
            raw_quotes = self.kite.ltp(instruments)

            # Extract LTP (already in RUPEES for Kite)
            ltp_map = {}
            for instrument_key, raw_data in raw_quotes.items():
                symbol = instrument_key.split(":")[-1]
                ltp = raw_data.get("last_price", 0)
                ltp_map[symbol] = Decimal(str(ltp))

            return ltp_map

        except Exception as e:
            logger.error(f"[Kite] get_ltp error: {e}")
            if "token" in str(e).lower() or "session" in str(e).lower():
                raise AuthenticationError("kite", str(e))
            raise BrokerAPIError("kite", f"Failed to get LTP: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to live ticks via WebSocket.

        Note: WebSocket is managed separately via KiteTickerService.
        This method is a placeholder for future WebSocket integration.

        Args:
            tokens: List of Kite instrument tokens
            mode: "ltp", "quote", or "full"
        """
        logger.warning("[Kite] subscribe() called on adapter - WebSocket managed separately")
        # TODO: Integrate with KiteTickerService

    async def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from live ticks."""
        logger.warning("[Kite] unsubscribe() called on adapter - WebSocket managed separately")
        # TODO: Integrate with KiteTickerService

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
            symbol: Canonical symbol (already in Kite format)
            from_date: Start date
            to_date: End date
            interval: "minute", "5minute", "15minute", "60minute", "day"

        Returns:
            List of OHLCV candles (prices in RUPEES)
        """
        try:
            # Get instrument token for the symbol
            token = await self._token_manager.get_token(symbol)
            if not token:
                raise InvalidSymbolError(symbol, "kite")

            # Map interval to Kite format
            interval_map = {
                "1min": "minute",
                "5min": "5minute",
                "15min": "15minute",
                "hour": "60minute",
                "day": "day",
            }
            kite_interval = interval_map.get(interval, "day")

            # Kite API expects datetime, not just date
            from_datetime = datetime.combine(from_date, time.min)
            to_datetime = datetime.combine(to_date, time.max)

            # Get historical data from Kite
            candles_data = self.kite.historical_data(
                instrument_token=token,
                from_date=from_datetime,
                to_date=to_datetime,
                interval=kite_interval
            )

            # Convert to OHLCVCandle
            candles = []
            for candle in candles_data:
                candles.append(OHLCVCandle(
                    timestamp=candle["date"],
                    open=Decimal(str(candle["open"])),  # Already in RUPEES
                    high=Decimal(str(candle["high"])),
                    low=Decimal(str(candle["low"])),
                    close=Decimal(str(candle["close"])),
                    volume=candle["volume"],
                    oi=candle.get("oi"),
                    raw_response=candle
                ))

            return candles

        except InvalidSymbolError:
            raise
        except Exception as e:
            logger.error(f"[Kite] get_historical error: {e}")
            if "token" in str(e).lower() or "session" in str(e).lower():
                raise AuthenticationError("kite", str(e))
            raise DataNotAvailableError("kite", str(e))

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
            # Get instruments from Kite
            raw_instruments = self.kite.instruments(exchange)

            # Convert to Instrument objects
            instruments = []
            for raw_inst in raw_instruments:
                try:
                    # Kite symbols are already canonical!
                    canonical_symbol = raw_inst["tradingsymbol"]

                    raw_type = raw_inst.get("instrument_type", "")
                    raw_strike = raw_inst.get("strike")
                    raw_expiry = raw_inst.get("expiry")

                    instruments.append(Instrument(
                        canonical_symbol=canonical_symbol,
                        exchange=exchange,
                        broker_symbol=canonical_symbol,  # Same as canonical for Kite
                        instrument_token=raw_inst["instrument_token"],
                        tradingsymbol=canonical_symbol,
                        name=raw_inst.get("name", canonical_symbol),
                        instrument_type=raw_type,
                        lot_size=raw_inst.get("lot_size", 1),
                        option_type=(
                            raw_type if raw_type in ("CE", "PE") else None
                        ),
                        strike=(
                            Decimal(str(raw_strike))
                            if raw_strike and float(raw_strike) > 0
                            else None
                        ),
                        expiry=(
                            raw_expiry.date()
                            if hasattr(raw_expiry, "date")
                            else raw_expiry
                        ),
                        underlying=raw_inst.get("name", ""),
                    ))
                except Exception as e:
                    # Skip instruments that fail conversion
                    logger.debug(f"[Kite] Skipping instrument: {e}")
                    continue

            return instruments

        except Exception as e:
            logger.error(f"[Kite] get_instruments error: {e}")
            if "token" in str(e).lower() or "session" in str(e).lower():
                raise AuthenticationError("kite", str(e))
            raise BrokerAPIError("kite", f"Failed to get instruments: {str(e)}")

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
            logger.error(f"[Kite] search_instruments error: {e}")
            raise BrokerAPIError("kite", f"Failed to search instruments: {str(e)}")

    async def get_token(self, symbol: str) -> int:
        """Get Kite instrument token for canonical symbol."""
        token = await self._token_manager.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(symbol, "kite")
        return token

    async def get_symbol(self, token: int) -> str:
        """Get canonical symbol for Kite instrument token."""
        symbol = await self._token_manager.get_symbol(token)
        if symbol is None:
            raise InvalidSymbolError(f"token:{token}", "kite")
        return symbol

    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self) -> bool:
        """
        Establish connection (validate access token and load token cache).

        Returns:
            True if successful
        """
        try:
            # Validate access token with a test API call
            profile = self.kite.profile()
            logger.info(f"[Kite] Connected for user: {profile.get('user_name', 'Unknown')}")

            # Load token cache for fast lookups
            await self._token_manager.load_cache()

            self._initialized = True
            logger.info("[Kite] Adapter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[Kite] Failed to connect: {e}")
            if "token" in str(e).lower() or "session" in str(e).lower():
                raise AuthenticationError("kite", str(e))
            return False

    async def disconnect(self) -> None:
        """Close connection gracefully."""
        # Nothing to disconnect for REST API
        logger.info("[Kite] Adapter disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._initialized

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def _convert_to_unified_quote(self, raw_data: dict, canonical_symbol: str) -> UnifiedQuote:
        """
        Convert Kite quote to UnifiedQuote.

        Args:
            raw_data: Raw quote from Kite
            canonical_symbol: Canonical symbol for this quote

        Returns:
            UnifiedQuote with prices in RUPEES (Kite already returns RUPEES)
        """
        ohlc = raw_data.get("ohlc", {})
        last_price = Decimal(str(raw_data.get("last_price", 0)))
        close_price = Decimal(str(ohlc.get("close", 0)))

        return UnifiedQuote(
            tradingsymbol=canonical_symbol,
            exchange=raw_data.get("exchange", "NFO"),
            instrument_token=raw_data.get("instrument_token"),
            last_price=last_price,
            open=Decimal(str(ohlc.get("open", 0))),
            high=Decimal(str(ohlc.get("high", 0))),
            low=Decimal(str(ohlc.get("low", 0))),
            close=close_price,
            change=raw_data.get("change", last_price - close_price),
            change_percent=Decimal(str(raw_data.get("change_percent", 0))),
            volume=raw_data.get("volume", 0),
            oi=raw_data.get("oi", 0),
            bid_price=Decimal(str(raw_data.get("depth", {}).get("buy", [{}])[0].get("price", 0))),
            bid_quantity=raw_data.get("depth", {}).get("buy", [{}])[0].get("quantity", 0),
            ask_price=Decimal(str(raw_data.get("depth", {}).get("sell", [{}])[0].get("price", 0))),
            ask_quantity=raw_data.get("depth", {}).get("sell", [{}])[0].get("quantity", 0),
            last_trade_time=raw_data.get("last_trade_time", datetime.now()),
            raw_response=raw_data
        )
