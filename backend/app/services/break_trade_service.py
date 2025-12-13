"""
Break Trade Service - Phase 5B

Implements the "Break/Split Trade" technique:
- Exit a losing leg
- Calculate recovery premium
- Split into two new positions (strangle recentering)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging
import uuid

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import (
    AutoPilotPositionLeg,
    AutoPilotStrategy,
    PositionLegStatus
)
from app.services.position_leg_service import PositionLegService
from app.services.strike_finder_service import StrikeFinderService
from app.services.leg_actions_service import LegActionsService
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class BreakTradeService:
    """Service for executing break/split trade adjustments."""

    def __init__(self, kite: KiteConnect, db: AsyncSession, user_id: str):
        self.kite = kite
        self.db = db
        self.user_id = user_id
        self.position_leg_service = PositionLegService(kite, db)
        self.strike_finder = StrikeFinderService(kite, db)
        self.leg_actions = LegActionsService(kite, db, user_id)
        self.market_data = MarketDataService(kite)

    def calculate_exit_cost(self, entry_price: Decimal, exit_price: Decimal, lot_size: int) -> Decimal:
        """Calculate the cost to exit a losing leg."""
        return (exit_price - entry_price) * lot_size

    def calculate_recovery_premiums(self, exit_price: Decimal, split_mode: str = "equal") -> Dict[str, Decimal]:
        """Calculate required premium for each new leg to recover exit cost.

        Args:
            exit_price: Price at which the losing leg was exited
            split_mode: How to split recovery premium (default: "equal")

        Returns:
            Dict with put_premium and call_premium
        """
        if split_mode == "equal":
            premium_per_leg = exit_price / Decimal("2")
        else:
            # Future: could implement weighted split
            premium_per_leg = exit_price / Decimal("2")

        return {
            "put_premium": premium_per_leg,
            "call_premium": premium_per_leg
        }

    async def find_new_strikes(
        self,
        expiry: str,
        put_premium: Decimal,
        call_premium: Decimal,
        underlying: str = "NIFTY",
        tolerance: Decimal = Decimal("10.00")
    ) -> dict:
        """Find new CE and PE strikes for break trade.

        Args:
            expiry: Expiry date in isoformat
            put_premium: Target premium for PUT
            call_premium: Target premium for CALL
            underlying: Underlying symbol (default: NIFTY)
            tolerance: Premium tolerance

        Returns:
            Dict with put_strike and call_strike
        """
        # Convert expiry string to date if needed
        if isinstance(expiry, str):
            from datetime import datetime
            expiry_date = datetime.fromisoformat(expiry).date()
        else:
            expiry_date = expiry

        # Find PE strike
        pe_result = await self.strike_finder.find_strike_by_premium(
            underlying=underlying,
            expiry=expiry_date,
            option_type="PE",
            target_premium=put_premium,
            tolerance=tolerance,
            prefer_round_strike=True
        )

        # Find CE strike
        ce_result = await self.strike_finder.find_strike_by_premium(
            underlying=underlying,
            expiry=expiry_date,
            option_type="CE",
            target_premium=call_premium,
            tolerance=tolerance,
            prefer_round_strike=True
        )

        return {
            "put_strike": pe_result["strike"] if pe_result else None,
            "call_strike": ce_result["strike"] if ce_result else None,
            "put_premium": pe_result.get("premium") if pe_result else None,
            "call_premium": ce_result.get("premium") if ce_result else None,
            "pe_premium": pe_result["premium"] if pe_result else None,
            "ce_strike": ce_result["strike"] if ce_result else None,
            "ce_premium": ce_result["premium"] if ce_result else None
        }

    async def break_trade(
        self,
        strategy_id: int,
        leg_id: str,
        execution_mode: str = "market",
        new_positions: str = "auto",
        new_put_strike: Optional[Decimal] = None,
        new_call_strike: Optional[Decimal] = None,
        premium_split: str = "equal",
        prefer_round_strikes: bool = True,
        max_delta: Decimal = Decimal('0.30')
    ) -> Dict[str, Any]:
        """
        Execute break/split trade on a losing leg.

        The algorithm:
        1. Exit the losing leg at current market price
        2. Calculate recovery premium = exit_price / 2
        3. Find new PUT strike with ~recovery premium
        4. Find new CALL strike with ~recovery premium
        5. Sell both new strikes to create a strangle

        Args:
            strategy_id: Strategy ID
            leg_id: Leg to break
            execution_mode: 'market' or 'limit'
            new_positions: 'auto' or 'manual'
            new_put_strike: Manual PUT strike (if new_positions='manual')
            new_call_strike: Manual CALL strike (if new_positions='manual')
            premium_split: 'equal' or 'weighted'
            prefer_round_strikes: Prefer round strikes
            max_delta: Maximum delta for new positions

        Returns:
            Dict with break trade details
        """
        try:
            # Step 1: Get the losing leg
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            if leg.status != PositionLegStatus.OPEN.value:
                raise ValueError(f"Leg {leg_id} is not open")

            # Get strategy
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)

            # Step 2: Get current price of the leg
            current_price = await self._get_current_price(leg.tradingsymbol)
            if not current_price:
                raise ValueError(f"Cannot get current price for {leg.tradingsymbol}")

            # Step 3: Calculate exit cost and recovery premium
            exit_cost = current_price  # This is the price we need to pay to exit
            recovery_premium_total = exit_cost

            logger.info(
                f"Break trade for {leg_id}: Exit cost = {exit_cost}, "
                f"Recovery premium = {recovery_premium_total}"
            )

            # Step 4: Calculate premium split for new positions
            if premium_split == "equal":
                put_target_premium = recovery_premium_total / 2
                call_target_premium = recovery_premium_total / 2
            else:  # weighted
                # Could weight based on volatility skew, for now use equal
                put_target_premium = recovery_premium_total / 2
                call_target_premium = recovery_premium_total / 2

            # Step 5: Find new strikes
            if new_positions == "auto":
                # Find strikes by premium
                new_strikes = await self._find_new_strikes_by_premium(
                    underlying=strategy.underlying,
                    expiry=leg.expiry,
                    put_target=put_target_premium,
                    call_target=call_target_premium,
                    prefer_round_strikes=prefer_round_strikes,
                    max_delta=max_delta
                )
            else:  # manual
                if not new_put_strike or not new_call_strike:
                    raise ValueError("Manual mode requires new_put_strike and new_call_strike")

                new_strikes = {
                    'put_strike': new_put_strike,
                    'call_strike': new_call_strike,
                    'put_premium': None,  # Will be fetched
                    'call_premium': None,
                }

            # Step 6: Exit the losing leg
            logger.info(f"Exiting losing leg {leg_id} at {current_price}")
            exit_result = await self.leg_actions.exit_leg(
                strategy_id=strategy_id,
                leg_id=leg_id,
                execution_mode=execution_mode
            )

            # Step 7: Create two new positions
            new_legs = await self._create_new_positions(
                strategy=strategy,
                original_leg=leg,
                put_strike=new_strikes['put_strike'],
                call_strike=new_strikes['call_strike'],
                lots=leg.lots
            )

            # Step 8: Calculate net cost
            total_premium_received = sum(
                Decimal(str(new_leg.get('premium', 0))) for new_leg in new_legs
            )
            net_cost = exit_cost - total_premium_received

            break_trade_id = f"bt_{uuid.uuid4().hex[:8]}"

            logger.info(
                f"Break trade {break_trade_id} completed: "
                f"Exit cost = {exit_cost}, "
                f"Premium received = {total_premium_received}, "
                f"Net cost = {net_cost}"
            )

            return {
                "break_trade_id": break_trade_id,
                "exit_order": {
                    "leg_id": leg_id,
                    "strike": leg.strike,
                    "exit_price": exit_result.get('exit_price'),
                    "realized_pnl": exit_result.get('realized_pnl')
                },
                "new_positions": new_legs,
                "recovery_premium": recovery_premium_total,
                "exit_cost": exit_cost,
                "net_cost": net_cost,
                "status": "executed"
            }

        except Exception as e:
            logger.error(f"Error executing break trade for leg {leg_id}: {e}")
            raise

    async def simulate_break_trade(
        self,
        strategy_id: int,
        leg_id: str,
        premium_split: str = "equal",
        prefer_round_strikes: bool = True,
        max_delta: Decimal = Decimal('0.30')
    ) -> Dict[str, Any]:
        """
        Simulate a break trade without executing.
        Returns what would happen if break trade is executed.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg to simulate breaking
            premium_split: 'equal' or 'weighted'
            prefer_round_strikes: Prefer round strikes
            max_delta: Maximum delta for new positions

        Returns:
            Simulation results
        """
        try:
            # Get the leg
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            # Get strategy
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)

            # Get current price
            current_price = await self._get_current_price(leg.tradingsymbol)
            if not current_price:
                raise ValueError(f"Cannot get current price for {leg.tradingsymbol}")

            # Calculate recovery premium
            exit_cost = current_price
            recovery_premium_total = exit_cost

            # Calculate split
            if premium_split == "equal":
                put_target = recovery_premium_total / 2
                call_target = recovery_premium_total / 2
            else:
                put_target = recovery_premium_total / 2
                call_target = recovery_premium_total / 2

            # Find new strikes
            new_strikes = await self._find_new_strikes_by_premium(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                put_target=put_target,
                call_target=call_target,
                prefer_round_strikes=prefer_round_strikes,
                max_delta=max_delta
            )

            return {
                "current_leg": {
                    "leg_id": leg_id,
                    "strike": leg.strike,
                    "option_type": leg.contract_type,
                    "current_price": current_price,
                    "entry_price": leg.entry_price,
                    "unrealized_pnl": leg.unrealized_pnl
                },
                "exit_cost": exit_cost,
                "recovery_premium_target": recovery_premium_total,
                "suggested_new_positions": [
                    {
                        "type": "PE",
                        "strike": new_strikes['put_strike'],
                        "premium": new_strikes.get('put_premium'),
                        "delta": new_strikes.get('put_delta')
                    },
                    {
                        "type": "CE",
                        "strike": new_strikes['call_strike'],
                        "premium": new_strikes.get('call_premium'),
                        "delta": new_strikes.get('call_delta')
                    }
                ],
                "estimated_net_cost": exit_cost - (
                    new_strikes.get('put_premium', 0) + new_strikes.get('call_premium', 0)
                )
            }

        except Exception as e:
            logger.error(f"Error simulating break trade: {e}")
            raise

    async def _get_current_price(self, tradingsymbol: str) -> Optional[Decimal]:
        """Get current market price for an option."""
        try:
            if not tradingsymbol:
                return None

            ltp_data = await self.market_data.get_ltp([f"NFO:{tradingsymbol}"])
            return ltp_data.get(f"NFO:{tradingsymbol}")
        except Exception as e:
            logger.error(f"Error getting current price for {tradingsymbol}: {e}")
            return None

    async def _find_new_strikes_by_premium(
        self,
        underlying: str,
        expiry: date,
        put_target: Decimal,
        call_target: Decimal,
        prefer_round_strikes: bool,
        max_delta: Decimal
    ) -> Dict[str, Any]:
        """
        Find new PUT and CALL strikes based on target premiums.

        Returns:
            Dict with put_strike, call_strike, and their details
        """
        try:
            # Find PUT strike
            put_result = await self.strike_finder.find_strike_by_premium(
                underlying=underlying,
                expiry=expiry,
                option_type="PE",
                target_premium=put_target,
                tolerance=Decimal('20'),  # ±20 rupees tolerance
                prefer_round_strike=prefer_round_strikes
            )

            # Find CALL strike
            call_result = await self.strike_finder.find_strike_by_premium(
                underlying=underlying,
                expiry=expiry,
                option_type="CE",
                target_premium=call_target,
                tolerance=Decimal('20'),
                prefer_round_strike=prefer_round_strikes
            )

            # Verify deltas are within acceptable range
            put_delta = abs(float(put_result.get('delta', 0)))
            call_delta = abs(float(call_result.get('delta', 0)))

            if put_delta > float(max_delta):
                logger.warning(
                    f"PUT delta {put_delta} exceeds max_delta {max_delta}, "
                    f"finding safer strike"
                )
                # Find by delta instead
                put_result = await self.strike_finder.find_strike_by_delta(
                    underlying=underlying,
                    expiry=expiry,
                    option_type="PE",
                    target_delta=max_delta,
                    prefer_round_strike=prefer_round_strikes
                )

            if call_delta > float(max_delta):
                logger.warning(
                    f"CALL delta {call_delta} exceeds max_delta {max_delta}, "
                    f"finding safer strike"
                )
                call_result = await self.strike_finder.find_strike_by_delta(
                    underlying=underlying,
                    expiry=expiry,
                    option_type="CE",
                    target_delta=max_delta,
                    prefer_round_strike=prefer_round_strikes
                )

            # Adjust CALL target if PUT premium is less than target
            actual_put_premium = put_result.get('ltp', 0)
            if actual_put_premium < put_target:
                # Increase CALL target to compensate
                call_target_adjusted = call_target + (put_target - actual_put_premium)
                logger.info(
                    f"Adjusting CALL target from {call_target} to {call_target_adjusted} "
                    f"to compensate for PUT shortfall"
                )
                call_result = await self.strike_finder.find_strike_by_premium(
                    underlying=underlying,
                    expiry=expiry,
                    option_type="CE",
                    target_premium=call_target_adjusted,
                    tolerance=Decimal('20'),
                    prefer_round_strike=prefer_round_strikes
                )

            return {
                'put_strike': put_result['strike'],
                'put_premium': put_result.get('ltp'),
                'put_delta': put_result.get('delta'),
                'call_strike': call_result['strike'],
                'call_premium': call_result.get('ltp'),
                'call_delta': call_result.get('delta'),
            }

        except Exception as e:
            logger.error(f"Error finding new strikes by premium: {e}")
            raise

    async def _create_new_positions(
        self,
        strategy: AutoPilotStrategy,
        original_leg: AutoPilotPositionLeg,
        put_strike: Decimal,
        call_strike: Decimal,
        lots: int
    ) -> List[Dict[str, Any]]:
        """Create two new position legs (PUT and CALL)."""
        try:
            new_legs = []

            # Create PUT leg
            put_leg_id = f"{original_leg.leg_id}_break_put_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            put_instrument = await self._get_instrument_details(
                underlying=strategy.underlying,
                expiry=original_leg.expiry,
                strike=put_strike,
                option_type="PE"
            )

            put_leg = await self.position_leg_service.create_position_leg(
                strategy_id=strategy.id,
                leg_id=put_leg_id,
                contract_type="PE",
                action="SELL",  # Break trade always sells new positions
                strike=put_strike,
                expiry=original_leg.expiry,
                lots=lots,
                tradingsymbol=put_instrument['tradingsymbol'],
                instrument_token=put_instrument.get('instrument_token'),
                entry_price=put_instrument.get('premium')
            )

            new_legs.append({
                "leg_id": put_leg_id,
                "type": "PE",
                "strike": put_strike,
                "premium": put_instrument.get('premium'),
                "delta": put_instrument.get('delta')
            })

            # Create CALL leg
            call_leg_id = f"{original_leg.leg_id}_break_call_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            call_instrument = await self._get_instrument_details(
                underlying=strategy.underlying,
                expiry=original_leg.expiry,
                strike=call_strike,
                option_type="CE"
            )

            call_leg = await self.position_leg_service.create_position_leg(
                strategy_id=strategy.id,
                leg_id=call_leg_id,
                contract_type="CE",
                action="SELL",
                strike=call_strike,
                expiry=original_leg.expiry,
                lots=lots,
                tradingsymbol=call_instrument['tradingsymbol'],
                instrument_token=call_instrument.get('instrument_token'),
                entry_price=call_instrument.get('premium')
            )

            new_legs.append({
                "leg_id": call_leg_id,
                "type": "CE",
                "strike": call_strike,
                "premium": call_instrument.get('premium'),
                "delta": call_instrument.get('delta')
            })

            return new_legs

        except Exception as e:
            logger.error(f"Error creating new positions: {e}")
            raise

    async def _get_instrument_details(
        self,
        underlying: str,
        expiry: date,
        strike: Decimal,
        option_type: str
    ) -> Dict[str, Any]:
        """Get instrument details including current premium."""
        # Construct tradingsymbol
        expiry_str = expiry.strftime("%y%b").upper()
        strike_str = str(int(strike))
        tradingsymbol = f"{underlying}{expiry_str}{strike_str}{option_type}"

        # Get current price
        ltp = await self._get_current_price(tradingsymbol)

        return {
            'tradingsymbol': tradingsymbol,
            'instrument_token': 0,  # Placeholder
            'premium': ltp,
            'strike': strike
        }
