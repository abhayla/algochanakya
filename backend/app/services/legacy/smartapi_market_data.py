"""
SmartAPI Market Data Service

REST API for on-demand quotes from AngelOne SmartAPI.
Used for after-market price checks and one-time price requests.
"""
import asyncio
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any

import requests
from SmartApi import SmartConnect

from app.services.legacy.smartapi_instruments import get_smartapi_instruments
from app.services.brokers.market_data.rate_limiter import broker_rate_limiters

logger = logging.getLogger(__name__)


class SmartAPIMarketDataError(Exception):
    """Exception raised for SmartAPI market data errors."""
    pass


class SmartAPIMarketData:
    """
    REST API service for on-demand quotes.

    Uses Market Data API for:
    - After-market price checks
    - One-time price snapshots
    - LTP/OHLC/Full quote requests
    """

    MODES = {
        'ltp': 'LTP',
        'ohlc': 'OHLC',
        'full': 'FULL'
    }

    # Kite symbol to SmartAPI token mapping for indices
    # These are hardcoded as index tokens don't change
    INDEX_TOKENS = {
        'NSE:NIFTY 50': {'token': '99926000', 'exchange': 'NSE', 'symbol': 'Nifty 50'},
        'NSE:NIFTY BANK': {'token': '99926009', 'exchange': 'NSE', 'symbol': 'Nifty Bank'},
        'NSE:NIFTY FIN SERVICE': {'token': '99926037', 'exchange': 'NSE', 'symbol': 'Nifty Fin Service'},
        'BSE:SENSEX': {'token': '99919000', 'exchange': 'BSE', 'symbol': 'SENSEX'},
        # Alternative names
        'NSE:NIFTY': {'token': '99926000', 'exchange': 'NSE', 'symbol': 'Nifty 50'},
        'NSE:BANKNIFTY': {'token': '99926009', 'exchange': 'NSE', 'symbol': 'Nifty Bank'},
        'NSE:FINNIFTY': {'token': '99926037', 'exchange': 'NSE', 'symbol': 'Nifty Fin Service'},
    }

    def __init__(self, api_key: str, jwt_token: str):
        """
        Initialize market data service.

        Args:
            api_key: AngelOne API key
            jwt_token: JWT token from authentication
        """
        self.api_key = api_key
        # Strip "Bearer " prefix if present - SDK expects raw token
        self.jwt_token = jwt_token.replace('Bearer ', '') if jwt_token else jwt_token
        self._api: Optional[SmartConnect] = None
        self._instruments = get_smartapi_instruments()

    def _get_api(self) -> SmartConnect:
        """Get or create SmartConnect instance."""
        if self._api is None:
            self._api = SmartConnect(api_key=self.api_key)
            self._api.setAccessToken(self.jwt_token)
        return self._api

    async def get_quote(
        self,
        exchange: str,
        tokens: List[str],
        mode: str = "FULL"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get current quote for instruments.

        Args:
            exchange: Exchange (NSE, NFO, etc.)
            tokens: List of SmartAPI tokens
            mode: LTP | OHLC | FULL

        Returns:
            Dict mapping token to quote data
        """
        try:
            api = self._get_api()

            # SmartAPI getMarketData expects mode and exchangeTokens as separate args
            mode_str = self.MODES.get(mode.lower(), mode)
            exchange_tokens = {exchange: tokens}

            logger.info(f"[SmartAPI] Fetching {mode} quote for {len(tokens)} tokens on {exchange}")

            # Rate limit: SmartAPI allows 1 request/second
            await broker_rate_limiters.acquire("smartapi")

            # Run synchronous SDK call in thread pool to avoid blocking the async event loop.
            # SmartAPI SDK uses synchronous requests — without this, each call blocks the entire
            # event loop for the duration of the HTTP round-trip (~3-8s), making 3 batches take 25s+.
            response = await asyncio.to_thread(api.getMarketData, mode_str, exchange_tokens)

            if not response or response.get('status') != True:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"[SmartAPI] Quote fetch failed: {error_msg}")
                raise SmartAPIMarketDataError(f"Quote fetch failed: {error_msg}")

            # Normalize response
            return self._normalize_quotes(response.get('data', {}), exchange)

        except SmartAPIMarketDataError:
            raise
        except Exception as e:
            logger.error(f"[SmartAPI] Quote error: {e}")
            raise SmartAPIMarketDataError(f"Quote fetch failed: {e}")

    def _normalize_quotes(
        self,
        data: Dict[str, Any],
        exchange: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Normalize SmartAPI quote response.

        Args:
            data: Raw response data
            exchange: Exchange name

        Returns:
            Dict mapping token to normalized quote
        """
        result = {}
        fetched = data.get('fetched', [])

        for quote in fetched:
            token = quote.get('symbolToken')
            if not token:
                continue

            # Build normalized quote (prices already in rupees from REST API)
            result[token] = {
                'token': token,
                'tradingsymbol': quote.get('tradingSymbol', ''),
                'exchange': exchange,
                'ltp': Decimal(str(quote.get('ltp', 0))),
                'open': Decimal(str(quote.get('open', 0))),
                'high': Decimal(str(quote.get('high', 0))),
                'low': Decimal(str(quote.get('low', 0))),
                'close': Decimal(str(quote.get('close', 0))),
                'volume': quote.get('tradeVolume', 0),
                'oi': quote.get('opnInterest', 0),
                'oi_change': quote.get('opnInterestChange', 0),
                'total_buy_qty': quote.get('totBuyQuan', 0),
                'total_sell_qty': quote.get('totSellQuan', 0),
                '52_week_high': Decimal(str(quote.get('52WeekHigh', 0))),
                '52_week_low': Decimal(str(quote.get('52WeekLow', 0))),
                'upper_circuit': Decimal(str(quote.get('upperCircuit', 0))),
                'lower_circuit': Decimal(str(quote.get('lowerCircuit', 0))),
                'last_trade_time': quote.get('exchTradeTime'),
                'exchange_timestamp': quote.get('exchFeedTime'),
                'depth': self._normalize_depth(quote.get('depth', {})),
            }

        return result

    def _normalize_depth(self, depth: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Normalize market depth data."""
        result = {'buy': [], 'sell': []}

        for side in ['buy', 'sell']:
            side_data = depth.get(side, [])
            for level in side_data:
                result[side].append({
                    'price': Decimal(str(level.get('price', 0))),
                    'quantity': level.get('quantity', 0),
                    'orders': level.get('orders', 0),
                })

        return result

    async def get_ltp(
        self,
        instruments: List[str]
    ) -> Dict[str, Decimal]:
        """
        Get last traded price for instruments.

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings (Kite format)

        Returns:
            Dict mapping instrument to LTP
        """
        result = {}

        # Separate index instruments from regular instruments
        index_instruments = []
        regular_instruments = []

        for inst in instruments:
            if inst.upper() in [k.upper() for k in self.INDEX_TOKENS.keys()]:
                index_instruments.append(inst)
            else:
                regular_instruments.append(inst)

        # Handle index instruments with hardcoded tokens
        if index_instruments:
            # Group index tokens by exchange
            index_by_exchange: Dict[str, List[tuple]] = {}
            for inst in index_instruments:
                # Find matching index token (case-insensitive)
                for key, info in self.INDEX_TOKENS.items():
                    if key.upper() == inst.upper():
                        exchange = info['exchange']
                        if exchange not in index_by_exchange:
                            index_by_exchange[exchange] = []
                        index_by_exchange[exchange].append((inst, info['token']))
                        break

            for exchange, token_pairs in index_by_exchange.items():
                tokens = [t[1] for t in token_pairs]
                original_keys = {t[1]: t[0] for t in token_pairs}

                try:
                    quotes = await self.get_quote(exchange, tokens, mode='LTP')
                    for token, quote in quotes.items():
                        original_key = original_keys.get(token)
                        if original_key:
                            result[original_key] = quote.get('ltp', Decimal(0))
                except Exception as e:
                    logger.warning(f"[SmartAPI] Failed to get index LTP: {e}")

        # Handle regular instruments
        if regular_instruments:
            by_exchange = self._group_by_exchange(regular_instruments)

            for exchange, symbols in by_exchange.items():
                tokens = []
                symbol_map = {}  # token -> original key

                for symbol in symbols:
                    token = await self._instruments.lookup_token(symbol, exchange)
                    if token:
                        tokens.append(token)
                        symbol_map[token] = f"{exchange}:{symbol}"

                if tokens:
                    quotes = await self.get_quote(exchange, tokens, mode='LTP')
                    for token, quote in quotes.items():
                        key = symbol_map.get(token)
                        if key:
                            result[key] = quote.get('ltp', Decimal(0))

        return result

    async def get_full_quote(
        self,
        instruments: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get full quote for instruments.

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings

        Returns:
            Dict mapping instrument to full quote data
        """
        result = {}

        # Separate index instruments from regular instruments
        index_instruments = []
        regular_instruments = []

        for inst in instruments:
            if inst.upper() in [k.upper() for k in self.INDEX_TOKENS.keys()]:
                index_instruments.append(inst)
            else:
                regular_instruments.append(inst)

        # Handle index instruments with hardcoded tokens
        if index_instruments:
            index_by_exchange: Dict[str, List[tuple]] = {}
            for inst in index_instruments:
                for key, info in self.INDEX_TOKENS.items():
                    if key.upper() == inst.upper():
                        exchange = info['exchange']
                        if exchange not in index_by_exchange:
                            index_by_exchange[exchange] = []
                        index_by_exchange[exchange].append((inst, info['token']))
                        break

            for exchange, token_pairs in index_by_exchange.items():
                tokens = [t[1] for t in token_pairs]
                original_keys = {t[1]: t[0] for t in token_pairs}

                try:
                    quotes = await self.get_quote(exchange, tokens, mode='FULL')
                    for token, quote in quotes.items():
                        original_key = original_keys.get(token)
                        if original_key:
                            result[original_key] = quote
                except Exception as e:
                    logger.warning(f"[SmartAPI] Failed to get index quote: {e}")

        # Handle regular instruments
        if regular_instruments:
            by_exchange = self._group_by_exchange(regular_instruments)

            for exchange, symbols in by_exchange.items():
                tokens = []
                symbol_map = {}

                for symbol in symbols:
                    token = await self._instruments.lookup_token(symbol, exchange)
                    if token:
                        tokens.append(token)
                        symbol_map[token] = f"{exchange}:{symbol}"

                if tokens:
                    quotes = await self.get_quote(exchange, tokens, mode='FULL')
                    for token, quote in quotes.items():
                        key = symbol_map.get(token)
                        if key:
                            result[key] = quote

        return result

    async def get_index_quote(
        self,
        index: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote for an index (NIFTY, BANKNIFTY, etc.).

        Args:
            index: Index name

        Returns:
            Quote data for the index
        """
        # Index tokens in SmartAPI (hardcoded as they don't change)
        index_tokens = {
            'NIFTY': {'exchange': 'NSE', 'token': '99926000'},
            'NIFTY 50': {'exchange': 'NSE', 'token': '99926000'},  # Alias
            'BANKNIFTY': {'exchange': 'NSE', 'token': '99926009'},
            'NIFTY BANK': {'exchange': 'NSE', 'token': '99926009'},  # Alias
            'FINNIFTY': {'exchange': 'NSE', 'token': '99926037'},
            'SENSEX': {'exchange': 'BSE', 'token': '99919000'},
        }

        index_info = index_tokens.get(index.upper())
        if not index_info:
            raise SmartAPIMarketDataError(f"Unknown index: {index}. Supported: {list(index_tokens.keys())}")

        quotes = await self.get_quote(
            index_info['exchange'],
            [index_info['token']],
            mode='FULL'
        )

        quote_data = quotes.get(index_info['token'])
        if not quote_data:
            raise SmartAPIMarketDataError(f"Empty quote response for index {index}")

        return quote_data

    async def get_option_chain(self, name: str, expiry_date: date) -> Optional[dict]:
        """
        Fetch full option chain via SmartAPI's dedicated /optionChain endpoint.

        This endpoint returns all strikes in one call with live prices, OI, IV,
        and Greeks. Unlike getMarketData, it returns data for all strikes regardless
        of whether they traded in the current session — solving the zero-LTP problem.

        Uses the SmartConnect SDK instance to obtain the correct authenticated headers
        (same as all other SDK calls), then makes a GET request with query params.

        Args:
            name: Underlying name (e.g., "NIFTY", "BANKNIFTY", "FINNIFTY")
            expiry_date: Python date object for the expiry

        Returns:
            Parsed response dict with 'data.fetched' list, or None on failure.
            Prices in the response are in RUPEES (not paise).
        """
        # Format expiry date as DDMMMYYYY (e.g., date(2026,3,17) → "17MAR2026")
        expiry_str = expiry_date.strftime("%d%b%Y").upper()

        logger.info(f"[SmartAPI] Fetching /optionChain for {name} expiry {expiry_str}")

        # Rate limit: SmartAPI allows 1 request/second
        await broker_rate_limiters.acquire("smartapi")

        def _do_request():
            api = self._get_api()
            # Build headers the same way the SDK does (requestHeaders + Authorization)
            headers = api.requestHeaders()
            if api.access_token:
                headers["Authorization"] = f"Bearer {api.access_token}"
            # Build URL from SDK root + path
            from urllib.parse import urljoin
            url = urljoin(api.root, "rest/secure/angelbroking/marketData/v1/optionChain")
            # Pass query params as proper key-value pairs (not JSON-encoded)
            query_params = {"name": name, "expirydate": expiry_str}
            resp = requests.get(
                url,
                params=query_params,
                headers=headers,
                verify=not api.disable_ssl,
                timeout=api.timeout,
                proxies=api.proxies,
            )
            if resp.status_code != 200:
                logger.error(
                    f"[SmartAPI] /optionChain HTTP {resp.status_code}: {resp.text[:200]}"
                )
                return None
            try:
                return resp.json()
            except Exception as parse_err:
                logger.error(
                    f"[SmartAPI] /optionChain JSON parse error: {parse_err}. "
                    f"Response text: {resp.text[:200]}"
                )
                return None

        try:
            data = await asyncio.to_thread(_do_request)
        except Exception as e:
            logger.error(f"[SmartAPI] /optionChain error for {name} {expiry_str}: {e}")
            return None

        if not data:
            logger.error(f"[SmartAPI] /optionChain returned empty/None response for {name} {expiry_str}")
            return None

        if not data.get("status"):
            msg = data.get("message", "Unknown error")
            logger.error(f"[SmartAPI] /optionChain API error for {name} {expiry_str}: {msg}")
            return None

        fetched = data.get("data", {}).get("fetched", [])
        logger.info(
            f"[SmartAPI] /optionChain returned {len(fetched)} strikes for {name} {expiry_str}"
        )
        return data

    def _group_by_exchange(self, instruments: List[str]) -> Dict[str, List[str]]:
        """
        Group instruments by exchange.

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings

        Returns:
            Dict mapping exchange to list of symbols
        """
        result: Dict[str, List[str]] = {}

        for inst in instruments:
            if ':' in inst:
                exchange, symbol = inst.split(':', 1)
            else:
                exchange = 'NFO'  # Default to NFO for options
                symbol = inst

            if exchange not in result:
                result[exchange] = []
            result[exchange].append(symbol)

        return result


def create_market_data_service(
    api_key: str,
    jwt_token: str
) -> SmartAPIMarketData:
    """
    Create a new SmartAPIMarketData instance.

    Args:
        api_key: AngelOne API key
        jwt_token: JWT token from authentication

    Returns:
        SmartAPIMarketData instance
    """
    return SmartAPIMarketData(api_key, jwt_token)
