"""
Instrument Token Manager

Manages mapping between canonical symbols and broker-specific tokens.
Caches tokens in memory for fast lookups, backed by database.

Database table: broker_instrument_tokens
- Maps: canonical_symbol + broker -> broker_token + broker_symbol
"""

import logging
from typing import Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages instrument token mappings for a specific broker.

    Provides fast in-memory lookup with database fallback.
    """

    def __init__(self, broker: str, db: AsyncSession):
        """
        Initialize token manager.

        Args:
            broker: Broker identifier (smartapi, kite, etc.)
            db: Database session
        """
        self.broker = broker
        self.db = db

        # In-memory caches
        self._symbol_to_token: Dict[str, int] = {}  # canonical -> broker token
        self._token_to_symbol: Dict[int, str] = {}  # broker token -> canonical
        self._symbol_to_broker_symbol: Dict[str, str] = {}  # canonical -> broker symbol

        self._loaded = False

    async def load_cache(self) -> None:
        """
        Load all tokens for this broker into memory.

        Called once on initialization. Subsequent lookups are instant.
        """
        if self._loaded:
            return

        try:
            # Import here to avoid circular dependency
            from app.models.broker_instrument_tokens import BrokerInstrumentToken

            # Load all tokens for this broker
            result = await self.db.execute(
                select(BrokerInstrumentToken).where(
                    BrokerInstrumentToken.broker == self.broker
                )
            )
            tokens = result.scalars().all()

            # Populate caches
            for token in tokens:
                self._symbol_to_token[token.canonical_symbol] = token.broker_token
                self._token_to_symbol[token.broker_token] = token.canonical_symbol
                self._symbol_to_broker_symbol[token.canonical_symbol] = token.broker_symbol

            logger.info(f"[{self.broker}] Loaded {len(tokens)} instrument tokens into cache")
            self._loaded = True

        except Exception as e:
            logger.error(f"[{self.broker}] Failed to load token cache: {e}")
            # Don't fail initialization - will fallback to database lookups
            self._loaded = False

    async def get_token(self, canonical_symbol: str) -> Optional[int]:
        """
        Get broker token for canonical symbol.

        Args:
            canonical_symbol: Symbol in Kite format (e.g., NIFTY25APR25000CE)

        Returns:
            Broker-specific instrument token, or None if not found
        """
        # Try cache first
        if canonical_symbol in self._symbol_to_token:
            return self._symbol_to_token[canonical_symbol]

        # Fallback to database
        try:
            from app.models.broker_instrument_tokens import BrokerInstrumentToken

            result = await self.db.execute(
                select(BrokerInstrumentToken).where(
                    BrokerInstrumentToken.canonical_symbol == canonical_symbol,
                    BrokerInstrumentToken.broker == self.broker
                )
            )
            mapping = result.scalar_one_or_none()

            if mapping:
                # Update cache
                self._symbol_to_token[canonical_symbol] = mapping.broker_token
                self._token_to_symbol[mapping.broker_token] = canonical_symbol
                self._symbol_to_broker_symbol[canonical_symbol] = mapping.broker_symbol
                return mapping.broker_token

        except Exception as e:
            logger.error(f"[{self.broker}] Failed to get token for {canonical_symbol}: {e}")

        return None

    async def get_symbol(self, broker_token: int) -> Optional[str]:
        """
        Get canonical symbol for broker token.

        Args:
            broker_token: Broker-specific instrument token

        Returns:
            Canonical symbol (Kite format), or None if not found
        """
        # Try cache first
        if broker_token in self._token_to_symbol:
            return self._token_to_symbol[broker_token]

        # Fallback to database
        try:
            from app.models.broker_instrument_tokens import BrokerInstrumentToken

            result = await self.db.execute(
                select(BrokerInstrumentToken).where(
                    BrokerInstrumentToken.broker_token == broker_token,
                    BrokerInstrumentToken.broker == self.broker
                )
            )
            mapping = result.scalar_one_or_none()

            if mapping:
                # Update cache
                self._symbol_to_token[mapping.canonical_symbol] = broker_token
                self._token_to_symbol[broker_token] = mapping.canonical_symbol
                self._symbol_to_broker_symbol[mapping.canonical_symbol] = mapping.broker_symbol
                return mapping.canonical_symbol

        except Exception as e:
            logger.error(f"[{self.broker}] Failed to get symbol for token {broker_token}: {e}")

        return None

    async def get_broker_symbol(self, canonical_symbol: str) -> Optional[str]:
        """
        Get broker-specific symbol for canonical symbol.

        Args:
            canonical_symbol: Symbol in Kite format

        Returns:
            Broker-specific symbol format, or None if not found
        """
        # Try cache first
        if canonical_symbol in self._symbol_to_broker_symbol:
            return self._symbol_to_broker_symbol[canonical_symbol]

        # Fallback to database
        try:
            from app.models.broker_instrument_tokens import BrokerInstrumentToken

            result = await self.db.execute(
                select(BrokerInstrumentToken).where(
                    BrokerInstrumentToken.canonical_symbol == canonical_symbol,
                    BrokerInstrumentToken.broker == self.broker
                )
            )
            mapping = result.scalar_one_or_none()

            if mapping:
                # Update cache
                self._symbol_to_token[canonical_symbol] = mapping.broker_token
                self._token_to_symbol[mapping.broker_token] = canonical_symbol
                self._symbol_to_broker_symbol[canonical_symbol] = mapping.broker_symbol
                return mapping.broker_symbol

        except Exception as e:
            logger.error(f"[{self.broker}] Failed to get broker symbol for {canonical_symbol}: {e}")

        return None

    async def get_mapping(self, canonical_symbol: str) -> Optional[Tuple[int, str]]:
        """
        Get both broker token and broker symbol for canonical symbol.

        Args:
            canonical_symbol: Symbol in Kite format

        Returns:
            Tuple of (broker_token, broker_symbol), or None if not found
        """
        token = await self.get_token(canonical_symbol)
        if token:
            broker_symbol = self._symbol_to_broker_symbol.get(canonical_symbol)
            if broker_symbol:
                return (token, broker_symbol)

        return None

    def cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "symbols_cached": len(self._symbol_to_token),
            "tokens_cached": len(self._token_to_symbol),
            "broker_symbols_cached": len(self._symbol_to_broker_symbol),
            "loaded": self._loaded
        }


class TokenManagerFactory:
    """
    Factory to create and cache TokenManager instances per broker.

    Ensures one TokenManager instance per broker throughout the application.
    """

    _instances: Dict[str, TokenManager] = {}

    @classmethod
    def get_manager(cls, broker: str, db: AsyncSession) -> TokenManager:
        """
        Get or create TokenManager for broker.

        Args:
            broker: Broker identifier
            db: Database session

        Returns:
            TokenManager instance for the broker
        """
        # Create new instance if not exists
        # Note: Each request gets a new DB session, so we create a new manager
        # The manager will load cache on first use
        return TokenManager(broker, db)
