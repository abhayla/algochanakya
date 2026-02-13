"""
OI Analysis Service

Provides Open Interest analysis including PCR, Max Pain, and OI Change tracking.
Used by AutoPilot condition engine for entry criteria.
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import asyncio
import logging

from app.models import Instrument
from app.services.legacy.market_data import MarketDataService

logger = logging.getLogger(__name__)


class OIAnalysisService:
    """Service for OI-based analysis (PCR, Max Pain, OI Change)"""

    # Cache TTL: 60 seconds for OI data (doesn't change rapidly)
    CACHE_TTL = 60

    def __init__(self, kite_client, db: AsyncSession):
        self.kite = kite_client
        self.db = db
        self.market_data = MarketDataService(kite_client)
        self._cache: Dict[str, Tuple[float, datetime]] = {}
        self._oi_history: Dict[str, Dict[float, int]] = {}  # Track previous OI

    async def get_pcr(self, underlying: str, expiry: str) -> float:
        """
        Get Put-Call Ratio for underlying and expiry.

        PCR = Total Put OI / Total Call OI

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            PCR value (e.g., 1.2 means more put OI than call OI)
        """
        cache_key = f"pcr:{underlying}:{expiry}"

        # Check cache
        if cache_key in self._cache:
            value, cached_at = self._cache[cache_key]
            if (datetime.now() - cached_at).total_seconds() < self.CACHE_TTL:
                return value

        try:
            # Get OI data from option chain
            oi_data = await self._get_oi_data(underlying, expiry)

            total_call_oi = sum(data["ce_oi"] for data in oi_data.values())
            total_put_oi = sum(data["pe_oi"] for data in oi_data.values())

            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

            # Cache result
            self._cache[cache_key] = (pcr, datetime.now())

            logger.info(f"PCR for {underlying} {expiry}: {pcr:.2f} (CE OI: {total_call_oi}, PE OI: {total_put_oi})")
            return pcr

        except Exception as e:
            logger.error(f"Error calculating PCR for {underlying} {expiry}: {e}")
            return 0.0

    async def get_max_pain(self, underlying: str, expiry: str) -> float:
        """
        Get Max Pain strike for underlying and expiry.

        Max Pain is the strike where option sellers lose the least money.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Max Pain strike price
        """
        cache_key = f"max_pain:{underlying}:{expiry}"

        # Check cache
        if cache_key in self._cache:
            value, cached_at = self._cache[cache_key]
            if (datetime.now() - cached_at).total_seconds() < self.CACHE_TTL:
                return value

        try:
            # Get OI data and spot price
            oi_data = await self._get_oi_data(underlying, expiry)
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = spot_data.ltp

            # Calculate max pain using existing algorithm
            max_pain_strike = self._calculate_max_pain(oi_data, spot_price)

            # Cache result
            self._cache[cache_key] = (max_pain_strike, datetime.now())

            logger.info(f"Max Pain for {underlying} {expiry}: {max_pain_strike} (Spot: {spot_price})")
            return max_pain_strike

        except Exception as e:
            logger.error(f"Error calculating Max Pain for {underlying} {expiry}: {e}")
            # Return spot price as fallback
            try:
                spot_data = await self.market_data.get_spot_price(underlying)
                return spot_data.ltp
            except:
                return 0.0

    async def get_oi_change_pct(self, underlying: str, expiry: str, strike: float, option_type: str) -> float:
        """
        Get OI change percentage for a specific strike.

        Compares current OI with OI from previous poll (1 minute ago).

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format
            strike: Strike price
            option_type: "CE" or "PE"

        Returns:
            OI change percentage (e.g., 15.5 means 15.5% increase)
        """
        history_key = f"{underlying}:{expiry}"
        oi_key = f"{strike}:{option_type}"

        try:
            # Get current OI data
            oi_data = await self._get_oi_data(underlying, expiry)

            if strike not in oi_data:
                return 0.0

            current_oi = oi_data[strike]["ce_oi"] if option_type == "CE" else oi_data[strike]["pe_oi"]

            # Get previous OI from history
            if history_key not in self._oi_history:
                # First time - store current OI and return 0
                self._oi_history[history_key] = {oi_key: current_oi}
                return 0.0

            previous_oi = self._oi_history[history_key].get(oi_key, current_oi)

            # Calculate change percentage
            if previous_oi > 0:
                change_pct = ((current_oi - previous_oi) / previous_oi) * 100
            else:
                change_pct = 0.0

            # Update history
            self._oi_history[history_key][oi_key] = current_oi

            logger.debug(f"OI Change for {underlying} {strike}{option_type}: {change_pct:.1f}% (Prev: {previous_oi}, Curr: {current_oi})")
            return change_pct

        except Exception as e:
            logger.error(f"Error calculating OI change for {underlying} {strike}{option_type}: {e}")
            return 0.0

    async def get_atm_oi_change(self, underlying: str, expiry: str) -> float:
        """
        Get combined ATM OI change (both CE and PE).

        Useful for detecting sudden interest at ATM strikes.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Average OI change percentage at ATM
        """
        try:
            # Get spot price to find ATM
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = spot_data.ltp

            # Get OI data
            oi_data = await self._get_oi_data(underlying, expiry)

            # Find ATM strike (nearest to spot)
            atm_strike = min(oi_data.keys(), key=lambda x: abs(x - spot_price))

            # Get OI change for both CE and PE
            ce_change = await self.get_oi_change_pct(underlying, expiry, atm_strike, "CE")
            pe_change = await self.get_oi_change_pct(underlying, expiry, atm_strike, "PE")

            # Return average
            avg_change = (ce_change + pe_change) / 2

            logger.info(f"ATM OI Change for {underlying} {atm_strike}: {avg_change:.1f}% (CE: {ce_change:.1f}%, PE: {pe_change:.1f}%)")
            return avg_change

        except Exception as e:
            logger.error(f"Error calculating ATM OI change for {underlying} {expiry}: {e}")
            return 0.0

    async def _get_oi_data(self, underlying: str, expiry: str) -> Dict[float, Dict[str, int]]:
        """
        Get OI data for all strikes.

        Returns dict: {strike: {"ce_oi": int, "pe_oi": int}}
        """
        try:
            # Parse expiry date
            if isinstance(expiry, str):
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            else:
                expiry_date = expiry

            # Get instruments for this expiry
            query = select(Instrument).where(
                and_(
                    Instrument.name == underlying,
                    Instrument.expiry == expiry_date,
                    Instrument.instrument_type.in_(["CE", "PE"]),
                    Instrument.exchange == "NFO"
                )
            ).order_by(Instrument.strike)

            result = await self.db.execute(query)
            instruments = result.scalars().all()

            if not instruments:
                logger.warning(f"No instruments found for {underlying} {expiry}")
                return {}

            # Organize by strike
            strikes_data = {}
            for inst in instruments:
                strike = float(inst.strike)
                if strike not in strikes_data:
                    strikes_data[strike] = {"ce_oi": 0, "pe_oi": 0}

            # Get quotes (OI data)
            instrument_symbols = [f"NFO:{inst.tradingsymbol}" for inst in instruments]

            # Batch in groups of 500
            all_quotes = {}
            for i in range(0, len(instrument_symbols), 500):
                batch = instrument_symbols[i:i+500]
                if batch:
                    try:
                        quotes = await asyncio.to_thread(self.kite.quote, batch)
                        all_quotes.update(quotes)
                    except Exception as e:
                        logger.error(f"Error fetching quotes batch {i}: {e}")

            # Extract OI data
            for inst in instruments:
                strike = float(inst.strike)
                symbol = f"NFO:{inst.tradingsymbol}"
                quote = all_quotes.get(symbol, {})
                oi = quote.get("oi", 0)

                if inst.instrument_type == "CE":
                    strikes_data[strike]["ce_oi"] = oi
                else:
                    strikes_data[strike]["pe_oi"] = oi

            return strikes_data

        except Exception as e:
            logger.error(f"Error fetching OI data for {underlying} {expiry}: {e}")
            return {}

    def _calculate_max_pain(self, oi_data: Dict[float, Dict], spot: float) -> float:
        """
        Calculate Max Pain strike.

        Max Pain is the strike where option writers lose the least money.

        Args:
            oi_data: {strike: {"ce_oi": int, "pe_oi": int}}
            spot: Current spot price

        Returns:
            Max Pain strike price
        """
        if not oi_data:
            return spot

        min_pain = float('inf')
        max_pain_strike = spot

        strikes = sorted(oi_data.keys())

        for test_strike in strikes:
            total_pain = 0

            for strike, data in oi_data.items():
                # CE pain: If spot > strike, CE is ITM
                if test_strike > strike:
                    ce_pain = (test_strike - strike) * data["ce_oi"]
                else:
                    ce_pain = 0

                # PE pain: If spot < strike, PE is ITM
                if test_strike < strike:
                    pe_pain = (strike - test_strike) * data["pe_oi"]
                else:
                    pe_pain = 0

                total_pain += ce_pain + pe_pain

            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = test_strike

        return max_pain_strike

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        logger.info("OI Analysis cache cleared")

    def clear_history(self):
        """Clear OI history (for testing)"""
        self._oi_history.clear()
        logger.info("OI history cleared")
