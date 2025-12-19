"""
Option Chain Service - Phase 5

Fetches and caches option chain data with Greeks.
Provides strike lookup by delta and premium.
"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.autopilot import AutoPilotOptionChainCache
from app.services.greeks_calculator import GreeksCalculatorService
from app.services.market_data import MarketDataService
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class OptionChainEntry:
    """Single option in the chain."""
    instrument_token: int
    tradingsymbol: str
    strike: Decimal
    option_type: str  # CE or PE
    expiry: date
    ltp: Optional[Decimal] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    oi_change: Optional[int] = None
    iv: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None


class OptionChainService:
    """Service for fetching and caching option chain data."""

    # Lot sizes for underlyings
    LOT_SIZES = {
        "NIFTY": 25,
        "BANKNIFTY": 15,
        "FINNIFTY": 25,
        "SENSEX": 10,
    }

    # Risk-free rate for Greeks calculation
    RISK_FREE_RATE = 0.07  # 7% for India

    # Cache TTL (time to live) in seconds
    CACHE_TTL = 2  # 2 seconds for option chain cache

    def __init__(self, kite: KiteConnect, db: AsyncSession, user_id: Optional[str] = None):
        self.kite = kite
        self.db = db
        self.greeks_calc = GreeksCalculatorService(db, user_id) if user_id else None
        self.market_data = MarketDataService(kite)

    async def get_option_chain(
        self,
        underlying: str,
        expiry: date,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get full option chain for underlying and expiry.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date
            use_cache: Whether to use cached data

        Returns:
            Dict with option chain data
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cached_data = await self._get_from_cache(underlying, expiry)
                if cached_data:
                    logger.info(f"Returning cached option chain for {underlying} {expiry}")
                    return cached_data

            # Fetch fresh data from Kite
            logger.info(f"Fetching fresh option chain for {underlying} {expiry}")

            # Get instruments for this underlying and expiry
            instruments = await self._fetch_instruments(underlying, expiry)

            if not instruments:
                logger.warning(f"No instruments found for {underlying} {expiry}")
                return {
                    "underlying": underlying,
                    "expiry": expiry,
                    "spot_price": None,
                    "options": [],
                    "cached": False,
                }

            # Get spot price
            spot_price = await self._get_spot_price(underlying)

            # Get LTPs for all instruments
            instrument_keys = [f"NFO:{inst['tradingsymbol']}" for inst in instruments]
            ltp_data = await self.market_data.get_ltp(instrument_keys)

            # Get quotes for OI, volume, etc.
            quote_data = await self._get_quotes(instrument_keys)

            # Build option chain entries with Greeks
            options = []
            for inst in instruments:
                key = f"NFO:{inst['tradingsymbol']}"
                ltp = ltp_data.get(key)
                quote = quote_data.get(key, {})

                # Calculate Greeks if we have price and spot
                greeks = {}
                if ltp and spot_price:
                    greeks = await self._calculate_greeks(
                        spot_price=spot_price,
                        strike=Decimal(str(inst['strike'])),
                        expiry=expiry,
                        option_type=inst['instrument_type'],
                        price=ltp
                    )

                entry = OptionChainEntry(
                    instrument_token=inst['instrument_token'],
                    tradingsymbol=inst['tradingsymbol'],
                    strike=Decimal(str(inst['strike'])),
                    option_type=inst['instrument_type'],
                    expiry=expiry,
                    ltp=ltp,
                    bid=Decimal(str(quote.get('depth', {}).get('buy', [{}])[0].get('price', 0))) if quote.get('depth') else None,
                    ask=Decimal(str(quote.get('depth', {}).get('sell', [{}])[0].get('price', 0))) if quote.get('depth') else None,
                    volume=quote.get('volume'),
                    oi=quote.get('oi'),
                    oi_change=quote.get('oi_day_high', 0) - quote.get('oi_day_low', 0) if quote.get('oi_day_high') else None,
                    iv=greeks.get('iv'),
                    delta=greeks.get('delta'),
                    gamma=greeks.get('gamma'),
                    theta=greeks.get('theta'),
                    vega=greeks.get('vega'),
                )
                options.append(entry)

            # Cache the data
            if use_cache:
                await self._save_to_cache(underlying, expiry, options)

            return {
                "underlying": underlying,
                "expiry": expiry,
                "spot_price": spot_price,
                "options": [self._entry_to_dict(opt) for opt in options],
                "cached": False,
                "cached_at": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            raise

    async def get_strikes_list(
        self,
        underlying: str,
        expiry: date
    ) -> List[Decimal]:
        """
        Get list of available strikes.

        Args:
            underlying: Index name
            expiry: Expiry date

        Returns:
            List of strike prices
        """
        instruments = await self._fetch_instruments(underlying, expiry)
        strikes = sorted(set(Decimal(str(inst['strike'])) for inst in instruments))
        return strikes

    async def _fetch_instruments(self, underlying: str, expiry: date) -> List[Dict]:
        """Fetch instruments from Kite for underlying and expiry."""
        loop = asyncio.get_event_loop()
        all_instruments = await loop.run_in_executor(
            None,
            self.kite.instruments,
            "NFO"
        )

        # Filter for this underlying and expiry
        expiry_str = expiry.strftime("%Y-%m-%d")
        filtered = [
            inst for inst in all_instruments
            if inst['name'] == underlying
            and inst['expiry'].strftime("%Y-%m-%d") == expiry_str
            and inst['instrument_type'] in ['CE', 'PE']
        ]

        return filtered

    async def _get_spot_price(self, underlying: str) -> Optional[Decimal]:
        """Get current spot price for underlying."""
        try:
            spot_data = await self.market_data.get_spot_price(underlying)
            return spot_data.ltp if spot_data else None
        except Exception as e:
            logger.error(f"Error fetching spot price for {underlying}: {e}")
            return None

    async def _get_quotes(self, instrument_keys: List[str]) -> Dict[str, Dict]:
        """Get full quotes for instruments."""
        try:
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                instrument_keys
            )
            return quote_data
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}

    async def _calculate_greeks(
        self,
        spot_price: Decimal,
        strike: Decimal,
        expiry: date,
        option_type: str,
        price: Decimal
    ) -> Dict[str, Optional[Decimal]]:
        """Calculate Greeks for an option."""
        try:
            # Check if Greeks calculator is initialized
            if self.greeks_calc is None:
                logger.warning("Greeks calculator not initialized (user_id not provided)")
                return {}

            # Calculate time to expiry
            from datetime import datetime
            tte = self.greeks_calc._calculate_time_to_expiry(expiry, datetime.now())

            if tte <= 0:
                return {}

            # Calculate IV from price
            iv = self.greeks_calc.calculate_iv_from_price(
                spot_price=float(spot_price),
                strike=float(strike),
                time_to_expiry=tte,
                option_price=float(price),
                option_type=option_type,
                risk_free_rate=self.RISK_FREE_RATE
            )

            # Calculate Greeks
            greeks = self.greeks_calc._calculate_greeks(
                spot_price=float(spot_price),
                strike=float(strike),
                time_to_expiry=tte,
                volatility=iv,
                risk_free_rate=self.RISK_FREE_RATE,
                option_type=option_type
            )

            return {
                'iv': Decimal(str(round(iv * 100, 2))),  # Convert to percentage
                'delta': Decimal(str(round(greeks['delta'], 4))),
                'gamma': Decimal(str(round(greeks['gamma'], 6))),
                'theta': Decimal(str(round(greeks['theta'], 2))),
                'vega': Decimal(str(round(greeks['vega'], 4))),
            }
        except Exception as e:
            logger.warning(f"Error calculating Greeks: {e}")
            return {}

    async def _get_from_cache(
        self,
        underlying: str,
        expiry: date
    ) -> Optional[Dict[str, Any]]:
        """Get option chain from cache."""
        try:
            # Check if cache is fresh (within TTL)
            cutoff_time = datetime.now() - timedelta(seconds=self.CACHE_TTL)

            query = select(AutoPilotOptionChainCache).where(
                and_(
                    AutoPilotOptionChainCache.underlying == underlying,
                    AutoPilotOptionChainCache.expiry == expiry,
                    AutoPilotOptionChainCache.updated_at >= cutoff_time
                )
            )

            result = await self.db.execute(query)
            cached_entries = result.scalars().all()

            if not cached_entries:
                return None

            # Build response from cache
            options = []
            for entry in cached_entries:
                options.append({
                    'instrument_token': entry.instrument_token,
                    'tradingsymbol': entry.tradingsymbol,
                    'strike': entry.strike,
                    'option_type': entry.option_type,
                    'expiry': entry.expiry,
                    'ltp': entry.ltp,
                    'bid': entry.bid,
                    'ask': entry.ask,
                    'volume': entry.volume,
                    'oi': entry.oi,
                    'oi_change': entry.oi_change,
                    'iv': entry.iv,
                    'delta': entry.delta,
                    'gamma': entry.gamma,
                    'theta': entry.theta,
                    'vega': entry.vega,
                })

            # Get spot price (not cached)
            spot_price = await self._get_spot_price(underlying)

            return {
                "underlying": underlying,
                "expiry": expiry,
                "spot_price": spot_price,
                "options": options,
                "cached": True,
                "cached_at": cached_entries[0].updated_at if cached_entries else None,
            }

        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None

    async def _save_to_cache(
        self,
        underlying: str,
        expiry: date,
        options: List[OptionChainEntry]
    ) -> None:
        """Save option chain to cache."""
        try:
            # Delete old cache entries for this underlying/expiry
            from sqlalchemy import delete
            delete_query = delete(AutoPilotOptionChainCache).where(
                and_(
                    AutoPilotOptionChainCache.underlying == underlying,
                    AutoPilotOptionChainCache.expiry == expiry
                )
            )
            await self.db.execute(delete_query)

            # Insert new cache entries
            for opt in options:
                cache_entry = AutoPilotOptionChainCache(
                    underlying=underlying,
                    expiry=expiry,
                    strike=opt.strike,
                    option_type=opt.option_type,
                    tradingsymbol=opt.tradingsymbol,
                    instrument_token=opt.instrument_token,
                    ltp=opt.ltp,
                    bid=opt.bid,
                    ask=opt.ask,
                    volume=opt.volume,
                    oi=opt.oi,
                    oi_change=opt.oi_change,
                    iv=opt.iv,
                    delta=opt.delta,
                    gamma=opt.gamma,
                    theta=opt.theta,
                    vega=opt.vega,
                )
                self.db.add(cache_entry)

            await self.db.commit()
            logger.info(f"Cached {len(options)} option chain entries for {underlying} {expiry}")

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            await self.db.rollback()

    def _entry_to_dict(self, entry: OptionChainEntry) -> Dict[str, Any]:
        """Convert OptionChainEntry to dict."""
        return {
            'instrument_token': entry.instrument_token,
            'tradingsymbol': entry.tradingsymbol,
            'strike': entry.strike,
            'option_type': entry.option_type,
            'expiry': entry.expiry,
            'ltp': entry.ltp,
            'bid': entry.bid,
            'ask': entry.ask,
            'volume': entry.volume,
            'oi': entry.oi,
            'oi_change': entry.oi_change,
            'iv': entry.iv,
            'delta': entry.delta,
            'gamma': entry.gamma,
            'theta': entry.theta,
            'vega': entry.vega,
        }
