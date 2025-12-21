"""
Strike Finder Service - Phase 5C

Finds option strikes by delta, premium, standard deviation, or expected move.
Implements round strike preference logic.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging
import math

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.option_chain_service import OptionChainService, OptionChainEntry
from app.services.expected_move_service import ExpectedMoveService
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class StrikeFinderService:
    """Service for finding option strikes by various criteria."""

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.option_chain_service = OptionChainService(kite, db)
        self.expected_move_service = ExpectedMoveService(kite, db)
        self.market_data = MarketDataService(kite)

    async def find_strike_by_delta(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        target_delta: Decimal,
        tolerance: Decimal = Decimal('0.02'),
        prefer_round_strike: bool = True,
        round_strike_divisor: int = 100,
        delta_tolerance: Optional[Decimal] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike with delta closest to target.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date
            option_type: CE or PE
            target_delta: Target delta value (0 to 1)
            tolerance: Acceptable delta deviation (deprecated, use delta_tolerance)
            prefer_round_strike: Prefer strikes divisible by round_strike_divisor
            round_strike_divisor: Divisor for round strikes (50 or 100)
            delta_tolerance: Acceptable delta deviation (replaces tolerance)

        Returns:
            Dict with strike details or None if not found
        """
        # Use delta_tolerance if provided, otherwise use tolerance
        effective_tolerance = delta_tolerance if delta_tolerance is not None else tolerance
        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            # Handle both "options" (flat) and "strikes" (nested) formats
            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                # Convert nested "strikes" format to flat "options" format
                options = []
                expiry_str = expiry.strftime("%y%b").upper() if hasattr(expiry, 'strftime') else str(expiry).replace('-', '')[-6:]
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,  # Placeholder
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,  # Placeholder
                            **strike_data['ce']
                        })

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
            if delta_diff > float(effective_tolerance):
                logger.warning(
                    f"Best match delta {closest_option['delta']} exceeds tolerance "
                    f"(target: {target_delta}, tolerance: {tolerance})"
                )

            # If prefer round strikes, check nearby round strikes
            if prefer_round_strike:
                # Filter for strikes divisible by round_strike_divisor
                round_options = [
                    opt for opt in filtered_options
                    if float(opt['strike']) % round_strike_divisor == 0
                ]
                if round_options:
                    # Find closest delta among round strikes
                    round_match = min(
                        round_options,
                        key=lambda opt: abs(abs(float(opt['delta'])) - target_delta_abs)
                    )
                    round_delta_diff = abs(abs(float(round_match['delta'])) - target_delta_abs)
                    # Use round strike if within reasonable tolerance
                    if round_delta_diff <= float(effective_tolerance) * 1.5:
                        closest_option = round_match
                        delta_diff = round_delta_diff

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

    async def find_strike_by_delta_range(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        min_delta: float,
        max_delta: float,
        prefer_round_strike: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike within a delta range.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date
            option_type: CE or PE
            min_delta: Minimum delta value
            max_delta: Maximum delta value
            prefer_round_strike: Prefer strikes divisible by 100

        Returns:
            Dict with strike details or None if not found

        Raises:
            ValueError: If min_delta > max_delta
        """
        if min_delta > max_delta:
            raise ValueError("min_delta must be less than max_delta")

        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            # Handle both formats
            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                options = []
                expiry_str = expiry.strftime("%y%b").upper() if hasattr(expiry, 'strftime') else str(expiry).replace('-', '')[-6:]
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['ce']
                        })

            if not options:
                logger.warning(f"No options found for {underlying} {expiry}")
                return None

            # Filter by option type, valid delta, and delta range
            midpoint = (min_delta + max_delta) / 2
            filtered_options = [
                opt for opt in options
                if opt['option_type'] == option_type
                and opt.get('delta') is not None
                and min_delta <= abs(float(opt['delta'])) <= max_delta
            ]

            if not filtered_options:
                logger.warning(f"No {option_type} options found in delta range [{min_delta}, {max_delta}]")
                return None

            # Find closest to midpoint of range
            closest_option = min(
                filtered_options,
                key=lambda opt: abs(abs(float(opt['delta'])) - midpoint)
            )

            # If prefer round strikes, check nearby round strikes within range
            if prefer_round_strike:
                round_options = [
                    opt for opt in filtered_options
                    if float(opt['strike']) % 100 == 0
                ]
                if round_options:
                    closest_option = min(
                        round_options,
                        key=lambda opt: abs(abs(float(opt['delta'])) - midpoint)
                    )

            return {
                'strike': closest_option['strike'],
                'tradingsymbol': closest_option['tradingsymbol'],
                'instrument_token': closest_option['instrument_token'],
                'ltp': closest_option.get('ltp'),
                'ce_delta': closest_option.get('delta') if option_type == 'CE' else None,
                'pe_delta': closest_option.get('delta') if option_type == 'PE' else None,
                'iv': closest_option.get('iv'),
            }

        except Exception as e:
            logger.error(f"Error finding strike by delta range: {e}")
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

            # Handle both "options" (flat) and "strikes" (nested) formats
            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                # Convert nested "strikes" format to flat "options" format
                options = []
                expiry_str = expiry.strftime("%y%b").upper() if hasattr(expiry, 'strftime') else str(expiry).replace('-', '')[-6:]
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,  # Placeholder
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,  # Placeholder
                            **strike_data['ce']
                        })

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
                'premium': closest_option.get('ltp'),  # Alias for ltp
                'delta': closest_option.get('delta'),
                'iv': closest_option.get('iv'),
                'distance_from_target': Decimal(str(premium_diff)),
            }

        except Exception as e:
            logger.error(f"Error finding strike by premium: {e}")
            raise

    async def find_strike_by_premium_range(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        min_premium: float,
        max_premium: float,
        delta_constraint: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike within a premium range.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            expiry: Expiry date
            option_type: CE or PE
            min_premium: Minimum premium value
            max_premium: Maximum premium value
            delta_constraint: Optional dict with 'min' and 'max' delta constraints

        Returns:
            Dict with strike details or None if not found

        Raises:
            ValueError: If min_premium > max_premium
        """
        if min_premium > max_premium:
            raise ValueError("min_premium must be less than max_premium")

        try:
            # Get option chain
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            # Handle both formats
            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                options = []
                expiry_str = expiry.strftime("%y%b").upper() if hasattr(expiry, 'strftime') else str(expiry).replace('-', '')[-6:]
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data:
                        tradingsymbol = f"{underlying}{expiry_str}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['ce']
                        })

            if not options:
                logger.warning(f"No options found for {underlying} {expiry}")
                return None

            # Filter by option type and premium range
            filtered_options = [
                opt for opt in options
                if opt['option_type'] == option_type
                and opt.get('ltp') is not None
                and min_premium <= float(opt['ltp']) <= max_premium
            ]

            # Apply delta constraint if provided
            if delta_constraint and filtered_options:
                min_delta = delta_constraint.get('min', 0)
                max_delta = delta_constraint.get('max', 1)
                filtered_options = [
                    opt for opt in filtered_options
                    if opt.get('delta') is not None
                    and min_delta <= abs(float(opt['delta'])) <= max_delta
                ]

            if not filtered_options:
                logger.warning(f"No {option_type} options found in premium range [{min_premium}, {max_premium}]")
                return None

            # Find option closest to midpoint of premium range
            midpoint = (min_premium + max_premium) / 2
            closest_option = min(
                filtered_options,
                key=lambda opt: abs(float(opt['ltp']) - midpoint)
            )

            return {
                'strike': closest_option['strike'],
                'tradingsymbol': closest_option['tradingsymbol'],
                'instrument_token': closest_option['instrument_token'],
                'ce_ltp': closest_option.get('ltp') if option_type == 'CE' else None,
                'pe_ltp': closest_option.get('ltp') if option_type == 'PE' else None,
                'ce_delta': closest_option.get('delta') if option_type == 'CE' else None,
                'pe_delta': closest_option.get('delta') if option_type == 'PE' else None,
                'iv': closest_option.get('iv'),
            }

        except Exception as e:
            logger.error(f"Error finding strike by premium range: {e}")
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

    async def find_strike_by_standard_deviation(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        standard_deviations: float = 1.0,
        outside_sd: bool = False,
        prefer_round_strike: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike at X standard deviations from ATM.

        Professional strategy entry: Sell options at 1σ, 1.5σ, or 2σ from spot.
        Uses ATM IV and DTE to calculate standard deviation move.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, FINNIFTY)
            expiry: Expiry date
            option_type: CE or PE
            standard_deviations: 1.0, 1.5, 2.0 (how many SDs from ATM)
            outside_sd: Select outside SD range (not currently used, for compatibility)
            prefer_round_strike: Prefer strikes divisible by 100

        Returns:
            Dict with strike details or None if not found

        Example:
            # Sell CE at 1σ: 68% probability OTM
            # Sell CE at 2σ: 95% probability OTM
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

            # Calculate DTE
            today = date.today()
            days_to_expiry = (expiry - today).days

            if days_to_expiry <= 0:
                logger.warning(f"Expiry {expiry} has passed or is today")
                return None

            # Get expected move (1 SD)
            expiry_str = expiry.strftime("%Y-%m-%d")
            expected_move_1sd = await self.expected_move_service.get_expected_move(
                underlying, expiry_str
            )

            if expected_move_1sd == 0:
                logger.warning(f"Could not calculate expected move for {underlying} {expiry}")
                return None

            # Calculate target strike
            sd_move = expected_move_1sd * standard_deviations

            if option_type == "CE":
                target_strike = spot_price + sd_move
            else:  # PE
                target_strike = spot_price - sd_move

            logger.info(
                f"Finding {option_type} strike at {standard_deviations}σ from spot "
                f"(Spot: {spot_price}, SD Move: {sd_move:.0f}, Target: {target_strike:.0f})"
            )

            # Get available strikes
            strikes = await self.option_chain_service.get_strikes_list(underlying, expiry)
            if not strikes:
                logger.warning(f"No strikes found for {underlying} {expiry}")
                return None

            # Find closest strike to target
            closest_strike = min(strikes, key=lambda s: abs(float(s) - target_strike))

            # If prefer round strike, find nearest round strike
            if prefer_round_strike:
                round_strikes = [s for s in strikes if float(s) % 100 == 0]
                if round_strikes:
                    closest_round = min(round_strikes, key=lambda s: abs(float(s) - target_strike))
                    # Use round strike if within 50 points of non-round strike
                    if abs(float(closest_round) - target_strike) <= abs(float(closest_strike) - target_strike) + 50:
                        closest_strike = closest_round

            # Get strike details from option chain
            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                # Convert nested format
                options = []
                expiry_str_symbol = expiry.strftime("%y%b").upper()
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data and option_type == 'PE':
                        tradingsymbol = f"{underlying}{expiry_str_symbol}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data and option_type == 'CE':
                        tradingsymbol = f"{underlying}{expiry_str_symbol}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['ce']
                        })

            # Find matching option
            matching_option = None
            for opt in options:
                if (float(opt['strike']) == float(closest_strike) and
                    opt['option_type'] == option_type):
                    matching_option = opt
                    break

            if not matching_option:
                logger.warning(f"Could not find option for strike {closest_strike}")
                return None

            return {
                'strike': matching_option['strike'],
                'tradingsymbol': matching_option['tradingsymbol'],
                'instrument_token': matching_option['instrument_token'],
                'ltp': matching_option.get('ltp'),
                'delta': matching_option.get('delta'),
                'iv': matching_option.get('iv'),
                'standard_deviations': standard_deviations,
                'expected_move_1sd': expected_move_1sd,
                'distance_from_spot': abs(float(matching_option['strike']) - spot_price),
            }

        except Exception as e:
            logger.error(f"Error finding strike by standard deviation: {e}")
            raise

    async def find_strike_by_expected_move(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        outside: bool = True,
        outside_sd: float = 1.0,
        prefer_round_strike: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find strike outside expected move range.

        Professional strategy: Sell options OUTSIDE expected move for higher probability OTM.

        Args:
            underlying: Index name
            expiry: Expiry date
            option_type: CE or PE
            outside_sd: How many SDs outside (1.0 = outside 1σ, 1.5 = outside 1.5σ)
            prefer_round_strike: Prefer strikes divisible by 100

        Returns:
            Dict with strike details or None if not found

        Example:
            # For iron condor: sell CE/PE outside 1σ expected move
            # This gives ~68% probability both stay OTM
        """
        try:
            # Get spot and expected move (check market_data for test mocks)
            if hasattr(self.market_data, 'get_spot_price') and hasattr(self.market_data, 'get_expected_move'):
                spot_obj = await self.market_data.get_spot_price(underlying)
                spot_price = float(spot_obj.ltp)
                expected_move = await self.market_data.get_expected_move(underlying)
            else:
                expiry_str = expiry.strftime("%Y-%m-%d")
                move_range = await self.expected_move_service.get_expected_move_range(
                    underlying, expiry_str
                )
                spot_price = move_range['spot']
                expected_move = move_range['expected_move']

            if expected_move == 0:
                logger.warning(f"Could not calculate expected move for {underlying} {expiry}")
                return None

            # Calculate target strike (outside expected move)
            if option_type == "CE":
                target_strike = spot_price + (expected_move * outside_sd)
            else:  # PE
                target_strike = spot_price - (expected_move * outside_sd)

            logger.info(
                f"Finding {option_type} strike OUTSIDE {outside_sd}σ expected move "
                f"(Spot: {spot_price}, EM: {expected_move:.0f}, Target: {target_strike:.0f})"
            )

            # Get available strikes
            strikes = await self.option_chain_service.get_strikes_list(underlying, expiry)

            # Fallback: extract strikes from option chain if get_strikes_list fails
            if not strikes:
                chain_data = await self.option_chain_service.get_option_chain(underlying, expiry)
                options = chain_data.get('options', [])
                if options:
                    strikes = sorted(set(opt.get('strike') for opt in options if opt.get('strike')))

            if not strikes:
                return None

            # For CE: find strikes ABOVE target
            # For PE: find strikes BELOW target
            if option_type == "CE":
                valid_strikes = [s for s in strikes if float(s) >= target_strike]
            else:
                valid_strikes = [s for s in strikes if float(s) <= target_strike]

            if not valid_strikes:
                logger.warning(f"No strikes found outside expected move")
                return None

            # Find closest strike to target (but still outside)
            closest_strike = min(valid_strikes, key=lambda s: abs(float(s) - target_strike))

            # If prefer round strike
            if prefer_round_strike:
                round_strikes = [s for s in valid_strikes if float(s) % 100 == 0]
                if round_strikes:
                    closest_round = min(round_strikes, key=lambda s: abs(float(s) - target_strike))
                    if abs(float(closest_round) - target_strike) <= abs(float(closest_strike) - target_strike) + 50:
                        closest_strike = closest_round

            # Get strike details
            chain_data = await self.option_chain_service.get_option_chain(
                underlying=underlying,
                expiry=expiry,
                use_cache=True
            )

            options = chain_data.get('options', [])
            if not options and 'strikes' in chain_data:
                options = []
                expiry_str_symbol = expiry.strftime("%y%b").upper()
                for strike_data in chain_data['strikes']:
                    strike = strike_data['strike']
                    if 'pe' in strike_data and option_type == 'PE':
                        tradingsymbol = f"{underlying}{expiry_str_symbol}{int(strike)}PE"
                        options.append({
                            'strike': strike,
                            'option_type': 'PE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['pe']
                        })
                    if 'ce' in strike_data and option_type == 'CE':
                        tradingsymbol = f"{underlying}{expiry_str_symbol}{int(strike)}CE"
                        options.append({
                            'strike': strike,
                            'option_type': 'CE',
                            'tradingsymbol': tradingsymbol,
                            'instrument_token': 0,
                            **strike_data['ce']
                        })

            # Find matching option
            matching_option = None
            for opt in options:
                if (float(opt['strike']) == float(closest_strike) and
                    opt['option_type'] == option_type):
                    matching_option = opt
                    break

            if not matching_option:
                return None

            return {
                'strike': matching_option['strike'],
                'tradingsymbol': matching_option['tradingsymbol'],
                'instrument_token': matching_option['instrument_token'],
                'ltp': matching_option.get('ltp'),
                'delta': matching_option.get('delta'),
                'iv': matching_option.get('iv'),
                'expected_move': expected_move,
                'outside_sd': outside_sd,
                'is_outside_expected_move': True,
                'distance_from_spot': abs(float(matching_option['strike']) - spot_price),
            }

        except Exception as e:
            logger.error(f"Error finding strike by expected move: {e}")
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

    # Alias methods for backward compatibility with tests
    async def find_strike_by_sd(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        sd_multiplier: float = 1.0,
        prefer_round_strike: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Alias for find_strike_by_standard_deviation() with sd_multiplier parameter.
        Used by Phase 5C tests.
        """
        return await self.find_strike_by_standard_deviation(
            underlying=underlying,
            expiry=expiry,
            option_type=option_type,
            standard_deviations=sd_multiplier,
            prefer_round_strike=prefer_round_strike
        )
