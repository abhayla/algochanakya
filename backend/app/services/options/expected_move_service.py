"""
Expected Move Service

Calculates the expected price move by expiration based on ATM straddle pricing.
Used for strike selection outside expected move range (professional strategy entry).
"""
from typing import Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import asyncio
import math
import logging

from app.models import Instrument
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class ExpectedMoveService:
    """Service for calculating expected move based on ATM straddle"""

    # Cache TTL: 300 seconds (5 minutes) - expected move doesn't change rapidly
    CACHE_TTL = 300

    # Expected move multiplier (0.85 is industry standard)
    # ATM Straddle Price × 0.85 = 1 standard deviation move
    STRADDLE_MULTIPLIER = 0.85

    def __init__(self, kite_client, db: AsyncSession):
        self.kite = kite_client
        self.db = db
        self.market_data = MarketDataService(kite_client)
        self._cache: Dict[str, Tuple[float, datetime]] = {}

    async def get_expected_move(self, underlying: str, expiry: str) -> float:
        """
        Calculate expected move by expiration.

        Expected Move = ATM Straddle Price × 0.85

        This represents the 1 standard deviation expected range.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Expected move in points (e.g., 250 means ±250 point move)
        """
        cache_key = f"expected_move:{underlying}:{expiry}"

        # Check cache
        if cache_key in self._cache:
            value, cached_at = self._cache[cache_key]
            if (datetime.now() - cached_at).total_seconds() < self.CACHE_TTL:
                return value

        try:
            # Get ATM straddle price
            atm_straddle = await self._get_atm_straddle_price(underlying, expiry)

            # Calculate expected move
            expected_move = atm_straddle * self.STRADDLE_MULTIPLIER

            # Cache result
            self._cache[cache_key] = (expected_move, datetime.now())

            logger.info(f"Expected Move for {underlying} {expiry}: ±{expected_move:.0f} (ATM Straddle: {atm_straddle:.0f})")
            return expected_move

        except Exception as e:
            logger.error(f"Error calculating expected move for {underlying} {expiry}: {e}")
            return 0.0

    async def get_expected_move_range(self, underlying: str, expiry: str) -> Dict[str, float]:
        """
        Get expected move range (upper and lower bounds).
        Uses multiple fallback strategies to ensure a value is always returned.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format

        Returns:
            Dict with spot, expected_move, upper_bound, lower_bound
        """
        spot_price = 0.0
        expected_move = 0.0

        # Step 1: Try to get spot price
        try:
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = float(spot_data.ltp)
            logger.info(f"Got spot price for {underlying}: {spot_price}")
        except Exception as e:
            logger.warning(f"Exception getting spot price for {underlying}: {e}")
            spot_price = 0.0

        # Step 2: Use fallback if spot is 0 or negative (regardless of exception)
        if spot_price <= 0:
            fallback_spots = {
                "NIFTY": 25900.0,
                "BANKNIFTY": 59000.0,
                "FINNIFTY": 24500.0,
                "SENSEX": 86000.0
            }
            spot_price = fallback_spots.get(underlying.upper(), 25000.0)
            logger.info(f"Using fallback spot price for {underlying}: {spot_price}")

        # Step 2: Calculate days to expiry
        try:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            dte = (expiry_date - datetime.now().date()).days
            if dte < 0:
                dte = 0
        except Exception as e:
            logger.warning(f"Failed to parse expiry {expiry}: {e}")
            dte = 4  # Default to 4 days

        # Step 3: Try ATM straddle method first
        try:
            expected_move = await self.get_expected_move(underlying, expiry)
        except Exception as e:
            logger.warning(f"ATM straddle method failed: {e}")
            expected_move = 0.0

        # Step 4: Fallback to VIX-based calculation if straddle returned 0
        if expected_move == 0 and dte > 0:
            logger.info(f"ATM straddle returned 0, falling back to VIX-based calculation")
            expected_move = await self._calculate_vix_based_expected_move(
                underlying, spot_price, dte
            )

        # Step 5: Calculate bounds
        upper_bound = spot_price + expected_move
        lower_bound = spot_price - expected_move

        logger.info(f"Expected Move Range for {underlying}: {lower_bound:.0f} - {upper_bound:.0f}")

        return {
            "spot": spot_price,
            "expected_move": expected_move,
            "expected_move_pct": (expected_move / spot_price) * 100 if spot_price > 0 else 0,
            "upper_bound": upper_bound,
            "lower_bound": lower_bound
        }

    async def get_expected_move_by_sd(self, underlying: str, expiry: str, standard_deviations: float = 1.0) -> float:
        """
        Get expected move for different standard deviations.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format
            standard_deviations: 1.0, 1.5, 2.0, etc.

        Returns:
            Expected move in points for given SD
        """
        try:
            # Get 1 SD expected move
            base_move = await self.get_expected_move(underlying, expiry)

            # Scale by standard deviations
            scaled_move = base_move * standard_deviations

            logger.info(f"Expected Move ({standard_deviations}σ) for {underlying} {expiry}: ±{scaled_move:.0f}")
            return scaled_move

        except Exception as e:
            logger.error(f"Error calculating {standard_deviations}σ expected move: {e}")
            return 0.0

    async def calculate_iv_based_expected_move(self, underlying: str, expiry: str, days_to_expiry: int) -> float:
        """
        Alternative calculation using IV directly.

        Expected Move = Spot × IV × √(DTE/365)

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format
            days_to_expiry: Days to expiration

        Returns:
            Expected move in points
        """
        try:
            # Get spot price
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = float(spot_data.ltp)

            # Get ATM IV
            atm_iv = await self._get_atm_iv(underlying, expiry)

            if atm_iv == 0:
                # Fallback to straddle-based calculation
                return await self.get_expected_move(underlying, expiry)

            # Calculate IV-based expected move
            # Expected Move = Spot × IV × √(DTE/365)
            iv_decimal = atm_iv / 100.0
            time_factor = math.sqrt(days_to_expiry / 365.0)
            expected_move = spot_price * iv_decimal * time_factor

            logger.info(f"IV-based Expected Move for {underlying}: ±{expected_move:.0f} (IV: {atm_iv}%, DTE: {days_to_expiry})")
            return expected_move

        except Exception as e:
            logger.error(f"Error calculating IV-based expected move: {e}")
            return 0.0

    async def is_strike_outside_expected_move(
        self,
        underlying: str,
        expiry: str,
        strike: float,
        option_type: str,
        standard_deviations: float = 1.0
    ) -> bool:
        """
        Check if a strike is outside the expected move range.

        Useful for selling options outside expected move (higher probability OTM).

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            expiry: Expiry date in YYYY-MM-DD format
            strike: Strike price to check
            option_type: "CE" or "PE"
            standard_deviations: 1.0, 1.5, 2.0

        Returns:
            True if strike is outside expected move
        """
        try:
            # Get expected move range
            move_range = await self.get_expected_move_range(underlying, expiry)

            # Scale by standard deviations
            upper_bound = move_range["spot"] + (move_range["expected_move"] * standard_deviations)
            lower_bound = move_range["spot"] - (move_range["expected_move"] * standard_deviations)

            # Check if outside range
            if option_type == "CE":
                is_outside = strike > upper_bound
            else:  # PE
                is_outside = strike < lower_bound

            logger.debug(f"Strike {strike}{option_type} outside {standard_deviations}σ EM? {is_outside} (Range: {lower_bound:.0f}-{upper_bound:.0f})")
            return is_outside

        except Exception as e:
            logger.error(f"Error checking if strike outside expected move: {e}")
            return False

    async def _get_atm_straddle_price(self, underlying: str, expiry: str) -> float:
        """
        Get ATM straddle price (CE + PE at ATM strike).

        Returns:
            ATM straddle price (sum of CE and PE premiums)
        """
        try:
            # Get spot price to find ATM
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = float(spot_data.ltp)

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
                return 0.0

            # Find ATM strike (nearest to spot)
            strikes = sorted(set(float(inst.strike) for inst in instruments))
            atm_strike = min(strikes, key=lambda x: abs(x - spot_price))

            # Find CE and PE instruments at ATM
            atm_ce = None
            atm_pe = None

            for inst in instruments:
                if float(inst.strike) == atm_strike:
                    if inst.instrument_type == "CE":
                        atm_ce = inst
                    else:
                        atm_pe = inst

            if not atm_ce or not atm_pe:
                logger.warning(f"Could not find ATM CE/PE for {underlying} {expiry} at strike {atm_strike}")
                return 0.0

            # Get quotes for CE and PE
            ce_symbol = f"NFO:{atm_ce.tradingsymbol}"
            pe_symbol = f"NFO:{atm_pe.tradingsymbol}"

            quotes = await asyncio.to_thread(self.kite.quote, [ce_symbol, pe_symbol])

            ce_ltp = quotes.get(ce_symbol, {}).get("last_price", 0)
            pe_ltp = quotes.get(pe_symbol, {}).get("last_price", 0)

            straddle_price = ce_ltp + pe_ltp

            logger.debug(f"ATM Straddle for {underlying} {atm_strike}: {straddle_price:.0f} (CE: {ce_ltp}, PE: {pe_ltp})")
            return straddle_price

        except Exception as e:
            logger.error(f"Error getting ATM straddle price: {e}")
            return 0.0

    async def _get_atm_iv(self, underlying: str, expiry: str) -> float:
        """
        Get ATM implied volatility (average of CE and PE IV).

        Returns:
            ATM IV as percentage (e.g., 15.5)
        """
        try:
            # Get spot price to find ATM
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = float(spot_data.ltp)

            # Parse expiry date
            if isinstance(expiry, str):
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            else:
                expiry_date = expiry

            # Get instruments
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
                return 0.0

            # Find ATM strike
            strikes = sorted(set(float(inst.strike) for inst in instruments))
            atm_strike = min(strikes, key=lambda x: abs(x - spot_price))

            # Find CE and PE at ATM
            atm_ce = None
            atm_pe = None

            for inst in instruments:
                if float(inst.strike) == atm_strike:
                    if inst.instrument_type == "CE":
                        atm_ce = inst
                    else:
                        atm_pe = inst

            if not atm_ce or not atm_pe:
                return 0.0

            # Get quotes
            ce_symbol = f"NFO:{atm_ce.tradingsymbol}"
            pe_symbol = f"NFO:{atm_pe.tradingsymbol}"

            quotes = await asyncio.to_thread(self.kite.quote, [ce_symbol, pe_symbol])

            # Get IV from quotes (if available)
            # Note: Kite doesn't provide IV directly, would need to calculate
            # For now, return 0 to trigger straddle-based calculation
            return 0.0

        except Exception as e:
            logger.error(f"Error getting ATM IV: {e}")
            return 0.0

    async def _calculate_vix_based_expected_move(
        self, underlying: str, spot_price: float, dte: int
    ) -> float:
        """
        Calculate expected move using VIX/India VIX.

        Formula: Expected Move = Spot × (VIX/100) × √(DTE/365)

        This is a fallback method when ATM straddle pricing is unavailable.

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            spot_price: Current spot price
            dte: Days to expiry

        Returns:
            Expected move in points
        """
        try:
            # Get VIX data (India VIX)
            vix_decimal = await self.market_data.get_vix()
            vix_value = float(vix_decimal)

            logger.info(f"VIX value fetched: {vix_value}%")

        except Exception as e:
            # If VIX fetch fails, use default reasonable value
            logger.warning(f"Could not fetch VIX, using default 14%: {e}")
            vix_value = 14.0

        try:
            # Calculate expected move using VIX formula
            # Expected Move = Spot × IV × √(DTE/365)
            iv_decimal = vix_value / 100.0
            time_factor = math.sqrt(dte / 365.0)
            expected_move = spot_price * iv_decimal * time_factor

            logger.info(
                f"VIX-based Expected Move for {underlying}: ±{expected_move:.0f} "
                f"(Spot: {spot_price:.0f}, VIX: {vix_value}%, DTE: {dte})"
            )
            return expected_move

        except Exception as e:
            logger.error(f"Error calculating VIX-based expected move: {e}")
            return 0.0

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        logger.info("Expected Move cache cleared")
