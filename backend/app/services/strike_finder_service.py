"""
Strike Finder Service - Phase 5

Finds option strikes by delta, premium, or other criteria.
Implements round strike preference logic.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.option_chain_service import OptionChainService, OptionChainEntry

logger = logging.getLogger(__name__)


class StrikeFinderService:
    """Service for finding option strikes by various criteria."""

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.option_chain_service = OptionChainService(kite, db)

    async def find_strike_by_delta(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        target_delta: Decimal,
        tolerance: Decimal = Decimal('0.02'),
        prefer_round_strike: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike with delta closest to target.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date
            option_type: CE or PE
            target_delta: Target delta value (0 to 1)
            tolerance: Acceptable delta deviation
            prefer_round_strike: Prefer strikes divisible by 100

        Returns:
            Dict with strike details or None if not found
        """
        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            options = chain_data.get('options', [])
            if not options:
                logger.warning(f"No options found for {underlying} {expiry}")
                return None

            # Filter by option type and valid delta
            filtered_options = [
                opt for opt in options
                if opt['option_type'] == option_type
                and opt.get('delta') is not None
            ]

            if not filtered_options:
                logger.warning(f"No {option_type} options with delta found")
                return None

            # Find closest delta
            # For CE: delta is positive (0 to 1)
            # For PE: delta is negative (-1 to 0), we work with absolute value
            target_delta_abs = abs(float(target_delta))

            closest_option = min(
                filtered_options,
                key=lambda opt: abs(abs(float(opt['delta'])) - target_delta_abs)
            )

            delta_diff = abs(abs(float(closest_option['delta'])) - target_delta_abs)

            # Check if within tolerance
            if delta_diff > float(tolerance):
                logger.warning(
                    f"Best match delta {closest_option['delta']} exceeds tolerance "
                    f"(target: {target_delta}, tolerance: {tolerance})"
                )

            # If prefer round strikes, check nearby round strikes
            if prefer_round_strike:
                closest_option = await self._prefer_round_strike(
                    options=filtered_options,
                    best_match=closest_option,
                    target_delta=target_delta_abs,
                    tolerance=float(tolerance)
                )

            return {
                'strike': closest_option['strike'],
                'tradingsymbol': closest_option['tradingsymbol'],
                'instrument_token': closest_option['instrument_token'],
                'ltp': closest_option.get('ltp'),
                'delta': closest_option.get('delta'),
                'iv': closest_option.get('iv'),
                'distance_from_target': Decimal(str(delta_diff)),
            }

        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            raise

    async def find_strike_by_premium(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        target_premium: Decimal,
        tolerance: Decimal = Decimal('10'),
        prefer_round_strike: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike with premium (LTP) closest to target.

        Args:
            underlying: Index name
            expiry: Expiry date
            option_type: CE or PE
            target_premium: Target premium value
            tolerance: Acceptable premium deviation
            prefer_round_strike: Prefer strikes divisible by 100

        Returns:
            Dict with strike details or None if not found
        """
        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            options = chain_data.get('options', [])
            if not options:
                logger.warning(f"No options found for {underlying} {expiry}")
                return None

            # Filter by option type and valid LTP
            filtered_options = [
                opt for opt in options
                if opt['option_type'] == option_type
                and opt.get('ltp') is not None
                and opt['ltp'] > 0
            ]

            if not filtered_options:
                logger.warning(f"No {option_type} options with LTP found")
                return None

            # Find closest premium
            target_premium_float = float(target_premium)

            closest_option = min(
                filtered_options,
                key=lambda opt: abs(float(opt['ltp']) - target_premium_float)
            )

            premium_diff = abs(float(closest_option['ltp']) - target_premium_float)

            # Check if within tolerance
            if premium_diff > float(tolerance):
                logger.warning(
                    f"Best match premium {closest_option['ltp']} exceeds tolerance "
                    f"(target: {target_premium}, tolerance: {tolerance})"
                )

            # If prefer round strikes, check nearby round strikes
            if prefer_round_strike:
                closest_option = await self._prefer_round_strike_by_premium(
                    options=filtered_options,
                    best_match=closest_option,
                    target_premium=target_premium_float,
                    tolerance=float(tolerance)
                )

            return {
                'strike': closest_option['strike'],
                'tradingsymbol': closest_option['tradingsymbol'],
                'instrument_token': closest_option['instrument_token'],
                'ltp': closest_option.get('ltp'),
                'delta': closest_option.get('delta'),
                'iv': closest_option.get('iv'),
                'distance_from_target': Decimal(str(premium_diff)),
            }

        except Exception as e:
            logger.error(f"Error finding strike by premium: {e}")
            raise

    async def find_strikes_in_range(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        min_value: Decimal,
        max_value: Decimal,
        range_type: str = 'premium'  # 'premium' or 'delta'
    ) -> List[Dict[str, Any]]:
        """
        Find all strikes within a range.

        Args:
            underlying: Index name
            expiry: Expiry date
            option_type: CE or PE
            min_value: Minimum value
            max_value: Maximum value
            range_type: 'premium' or 'delta'

        Returns:
            List of strikes within range
        """
        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            options = chain_data.get('options', [])
            if not options:
                return []

            # Filter by option type
            filtered_options = [
                opt for opt in options
                if opt['option_type'] == option_type
            ]

            # Filter by range
            result = []
            for opt in filtered_options:
                if range_type == 'premium':
                    value = opt.get('ltp')
                    if value and min_value <= value <= max_value:
                        result.append({
                            'strike': opt['strike'],
                            'tradingsymbol': opt['tradingsymbol'],
                            'instrument_token': opt['instrument_token'],
                            'ltp': opt.get('ltp'),
                            'delta': opt.get('delta'),
                            'iv': opt.get('iv'),
                        })
                elif range_type == 'delta':
                    value = opt.get('delta')
                    if value:
                        value_abs = abs(float(value))
                        if float(min_value) <= value_abs <= float(max_value):
                            result.append({
                                'strike': opt['strike'],
                                'tradingsymbol': opt['tradingsymbol'],
                                'instrument_token': opt['instrument_token'],
                                'ltp': opt.get('ltp'),
                                'delta': opt.get('delta'),
                                'iv': opt.get('iv'),
                            })

            return result

        except Exception as e:
            logger.error(f"Error finding strikes in range: {e}")
            raise

    async def find_atm_strike(
        self,
        underlying: str,
        expiry: date
    ) -> Optional[Decimal]:
        """
        Find ATM (At The Money) strike.

        Args:
            underlying: Index name
            expiry: Expiry date

        Returns:
            ATM strike price
        """
        try:
            # Get spot price
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            spot_price = chain_data.get('spot_price')
            if not spot_price:
                logger.warning(f"No spot price found for {underlying}")
                return None

            # Get available strikes
            strikes = await self.option_chain_service.get_strikes_list(underlying, expiry)
            if not strikes:
                return None

            # Find closest strike to spot
            atm_strike = min(strikes, key=lambda s: abs(float(s) - float(spot_price)))

            return atm_strike

        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            raise

    async def _prefer_round_strike(
        self,
        options: List[Dict[str, Any]],
        best_match: Dict[str, Any],
        target_delta: float,
        tolerance: float
    ) -> Dict[str, Any]:
        """
        Prefer round strike if equally close to target.

        Args:
            options: All available options
            best_match: Current best match
            target_delta: Target delta value
            tolerance: Acceptable tolerance

        Returns:
            Best option (possibly round strike)
        """
        best_match_delta_diff = abs(abs(float(best_match['delta'])) - target_delta)

        # Find all options within tolerance
        candidates = [
            opt for opt in options
            if abs(abs(float(opt['delta'])) - target_delta) <= tolerance
        ]

        if not candidates:
            return best_match

        # Among candidates, prefer round strikes (divisible by 100)
        round_candidates = [
            opt for opt in candidates
            if float(opt['strike']) % 100 == 0
        ]

        if round_candidates:
            # Return round strike closest to target
            return min(
                round_candidates,
                key=lambda opt: abs(abs(float(opt['delta'])) - target_delta)
            )

        return best_match

    async def _prefer_round_strike_by_premium(
        self,
        options: List[Dict[str, Any]],
        best_match: Dict[str, Any],
        target_premium: float,
        tolerance: float
    ) -> Dict[str, Any]:
        """
        Prefer round strike if premium equally close to target.

        Args:
            options: All available options
            best_match: Current best match
            target_premium: Target premium value
            tolerance: Acceptable tolerance

        Returns:
            Best option (possibly round strike)
        """
        # Find all options within tolerance
        candidates = [
            opt for opt in options
            if opt.get('ltp') is not None
            and abs(float(opt['ltp']) - target_premium) <= tolerance
        ]

        if not candidates:
            return best_match

        # Among candidates, prefer round strikes (divisible by 100)
        round_candidates = [
            opt for opt in candidates
            if float(opt['strike']) % 100 == 0
        ]

        if round_candidates:
            # Return round strike closest to target premium
            return min(
                round_candidates,
                key=lambda opt: abs(float(opt['ltp']) - target_premium)
            )

        return best_match
