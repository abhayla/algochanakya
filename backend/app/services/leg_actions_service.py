"""
Leg Actions Service - Phase 5B

Handles exit, shift, and roll operations for individual position legs.
Integrates with order executor for actual trade execution.
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
from app.services.order_executor import OrderExecutor
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class LegActionsService:
    """Service for performing actions on individual position legs."""

    def __init__(self, kite: KiteConnect, db: AsyncSession, user_id: str):
        self.kite = kite
        self.db = db
        self.user_id = user_id
        self.position_leg_service = PositionLegService(kite, db)
        self.strike_finder = StrikeFinderService(kite, db)
        self.market_data = MarketDataService(kite)
        self.order_executor = OrderExecutor(kite, self.market_data, self.strike_finder)

    async def exit_leg(
        self,
        strategy_id: int,
        leg_id: str,
        execution_mode: str = "market",
        limit_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Exit a single position leg.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            execution_mode: 'market' or 'limit'
            limit_price: Limit price if execution_mode is 'limit'

        Returns:
            Dict with exit details
        """
        try:
            # Get the leg
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            if leg.status != PositionLegStatus.OPEN.value:
                raise ValueError(f"Leg {leg_id} is not open (status: {leg.status})")

            # Get strategy for lot size calculation
            from app.constants import get_lot_size
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            lot_size = get_lot_size(strategy.underlying)
            quantity = leg.lots * lot_size

            # Determine order type and price
            order_type = "MARKET" if execution_mode == "market" else "LIMIT"
            order_price = limit_price if execution_mode == "limit" else None

            # Reverse transaction type (if bought, now sell; if sold, now buy)
            transaction_type = "SELL" if leg.action == "BUY" else "BUY"

            # Get current LTP for logging
            ltp = None
            if leg.tradingsymbol:
                ltp_data = await self.market_data.get_ltp([f"NFO:{leg.tradingsymbol}"])
                ltp = ltp_data.get(f"NFO:{leg.tradingsymbol}")

            # Place exit order via order executor
            # Note: We'll need to implement a direct order placement method
            order_details = await self._place_exit_order(
                strategy=strategy,
                leg=leg,
                transaction_type=transaction_type,
                order_type=order_type,
                quantity=quantity,
                price=order_price
            )

            # Update leg with exit details
            exit_price = order_details.get('executed_price') or ltp
            if exit_price:
                await self.position_leg_service.update_leg_exit(
                    strategy_id=strategy_id,
                    leg_id=leg_id,
                    exit_price=exit_price,
                    exit_order_ids=[order_details.get('order_id')],
                    exit_reason="manual_exit"
                )

            logger.info(f"Exited leg {leg_id}: {transaction_type} {quantity} @ {exit_price}")

            return {
                "leg_id": leg_id,
                "action": "exit",
                "order_details": order_details,
                "exit_price": exit_price,
                "realized_pnl": leg.realized_pnl,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error exiting leg {leg_id}: {e}")
            raise

    async def shift_leg(
        self,
        strategy_id: int,
        leg_id: str,
        target_strike: Optional[Decimal] = None,
        target_delta: Optional[Decimal] = None,
        shift_direction: Optional[str] = None,
        shift_amount: Optional[int] = None,
        execution_mode: str = "market",
        limit_offset: Decimal = Decimal('1.0')
    ) -> Dict[str, Any]:
        """
        Shift a leg to a new strike (same expiry).

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            target_strike: Specific target strike
            target_delta: Target delta for new strike
            shift_direction: 'closer' or 'further' from ATM
            shift_amount: Points to shift
            execution_mode: 'market' or 'limit'
            limit_offset: Offset for limit orders

        Returns:
            Dict with shift details
        """
        try:
            # Get the leg
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            if leg.status != PositionLegStatus.OPEN.value:
                raise ValueError(f"Leg {leg_id} is not open")

            # Get strategy
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)

            # Determine new strike
            new_strike = await self._determine_new_strike(
                strategy=strategy,
                leg=leg,
                target_strike=target_strike,
                target_delta=target_delta,
                shift_direction=shift_direction,
                shift_amount=shift_amount
            )

            # Exit current leg
            exit_result = await self.exit_leg(
                strategy_id=strategy_id,
                leg_id=leg_id,
                execution_mode=execution_mode
            )

            # Create new leg at new strike
            new_leg_id = f"{leg.leg_id}_shifted_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Get instrument details for new strike
            new_instrument = await self._get_instrument_for_strike(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                strike=new_strike,
                option_type=leg.contract_type
            )

            # Place entry order for new leg
            entry_order = await self._place_entry_order(
                strategy=strategy,
                tradingsymbol=new_instrument['tradingsymbol'],
                transaction_type=leg.action,
                quantity=leg.lots * self._get_lot_size(strategy.underlying),
                order_type="MARKET" if execution_mode == "market" else "LIMIT",
                price=None  # Will be determined by market or calculated
            )

            # Create new position leg
            new_leg = await self.position_leg_service.create_position_leg(
                strategy_id=strategy_id,
                leg_id=new_leg_id,
                contract_type=leg.contract_type,
                action=leg.action,
                strike=new_strike,
                expiry=leg.expiry,
                lots=leg.lots,
                tradingsymbol=new_instrument['tradingsymbol'],
                instrument_token=new_instrument['instrument_token'],
                entry_price=entry_order.get('executed_price')
            )

            # Mark old leg as rolled
            await self.position_leg_service.mark_leg_as_rolled(
                strategy_id=strategy_id,
                old_leg_id=leg_id,
                new_leg_id=new_leg.id
            )

            logger.info(f"Shifted leg {leg_id} from {leg.strike} to {new_strike}")

            return {
                "shift_id": f"shift_{uuid.uuid4().hex[:8]}",
                "old_leg": {
                    "leg_id": leg_id,
                    "strike": leg.strike,
                    "exit_price": exit_result.get('exit_price')
                },
                "new_leg": {
                    "leg_id": new_leg_id,
                    "strike": new_strike,
                    "entry_price": entry_order.get('executed_price')
                },
                "premium_change": Decimal(str(entry_order.get('executed_price', 0))) -
                                 Decimal(str(exit_result.get('exit_price', 0))),
                "status": "executed"
            }

        except Exception as e:
            logger.error(f"Error shifting leg {leg_id}: {e}")
            raise

    async def roll_leg(
        self,
        strategy_id: int,
        leg_id: str,
        target_expiry: date,
        target_strike: Optional[Decimal] = None,
        execution_mode: str = "market"
    ) -> Dict[str, Any]:
        """
        Roll a leg to a new expiry (and optionally new strike).

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            target_expiry: New expiry date
            target_strike: Optional new strike (defaults to same strike)
            execution_mode: 'market' or 'limit'

        Returns:
            Dict with roll details
        """
        try:
            # Get the leg
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            if leg.status != PositionLegStatus.OPEN.value:
                raise ValueError(f"Leg {leg_id} is not open")

            # Get strategy
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)

            # Use same strike if not specified
            new_strike = target_strike or leg.strike

            # Exit current leg
            exit_result = await self.exit_leg(
                strategy_id=strategy_id,
                leg_id=leg_id,
                execution_mode=execution_mode
            )

            # Get instrument for new expiry
            new_instrument = await self._get_instrument_for_strike(
                underlying=strategy.underlying,
                expiry=target_expiry,
                strike=new_strike,
                option_type=leg.contract_type
            )

            # Place entry order for new leg
            entry_order = await self._place_entry_order(
                strategy=strategy,
                tradingsymbol=new_instrument['tradingsymbol'],
                transaction_type=leg.action,
                quantity=leg.lots * self._get_lot_size(strategy.underlying),
                order_type="MARKET",
                price=None
            )

            # Create new position leg
            new_leg_id = f"{leg.leg_id}_rolled_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            new_leg = await self.position_leg_service.create_position_leg(
                strategy_id=strategy_id,
                leg_id=new_leg_id,
                contract_type=leg.contract_type,
                action=leg.action,
                strike=new_strike,
                expiry=target_expiry,
                lots=leg.lots,
                tradingsymbol=new_instrument['tradingsymbol'],
                instrument_token=new_instrument['instrument_token'],
                entry_price=entry_order.get('executed_price')
            )

            # Mark old leg as rolled
            await self.position_leg_service.mark_leg_as_rolled(
                strategy_id=strategy_id,
                old_leg_id=leg_id,
                new_leg_id=new_leg.id
            )

            # Calculate roll cost/credit
            roll_cost = Decimal(str(entry_order.get('executed_price', 0))) - \
                       Decimal(str(exit_result.get('exit_price', 0)))

            logger.info(f"Rolled leg {leg_id} from {leg.expiry} to {target_expiry}")

            return {
                "roll_id": f"roll_{uuid.uuid4().hex[:8]}",
                "old_leg": {
                    "expiry": leg.expiry,
                    "strike": leg.strike
                },
                "new_leg": {
                    "expiry": target_expiry,
                    "strike": new_strike
                },
                "roll_cost": roll_cost,  # Negative means credit
                "status": "executed"
            }

        except Exception as e:
            logger.error(f"Error rolling leg {leg_id}: {e}")
            raise

    async def _determine_new_strike(
        self,
        strategy: AutoPilotStrategy,
        leg: AutoPilotPositionLeg,
        target_strike: Optional[Decimal],
        target_delta: Optional[Decimal],
        shift_direction: Optional[str],
        shift_amount: Optional[int]
    ) -> Decimal:
        """Determine the new strike for shift operation."""

        if target_strike:
            return target_strike

        if target_delta:
            # Find strike by delta
            result = await self.strike_finder.find_strike_by_delta(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                option_type=leg.contract_type,
                target_delta=target_delta,
                prefer_round_strike=True
            )
            return result['strike']

        if shift_direction and shift_amount:
            # Shift by amount
            if shift_direction == "closer":
                # Move closer to ATM
                atm_strike = await self.strike_finder.find_atm_strike(
                    underlying=strategy.underlying,
                    expiry=leg.expiry
                )
                if leg.contract_type == "CE":
                    new_strike = leg.strike - shift_amount
                else:  # PE
                    new_strike = leg.strike + shift_amount
            else:  # further
                # Move further from ATM
                if leg.contract_type == "CE":
                    new_strike = leg.strike + shift_amount
                else:  # PE
                    new_strike = leg.strike - shift_amount

            return Decimal(str(new_strike))

        raise ValueError("Must specify target_strike, target_delta, or shift_direction+shift_amount")

    async def _get_instrument_for_strike(
        self,
        underlying: str,
        expiry: date,
        strike: Decimal,
        option_type: str
    ) -> Dict[str, Any]:
        """Get instrument details for a strike."""
        # This would query Kite instruments
        # For now, construct tradingsymbol
        expiry_str = expiry.strftime("%y%b").upper()  # e.g., 24DEC
        strike_str = str(int(strike))
        tradingsymbol = f"{underlying}{expiry_str}{strike_str}{option_type}"

        # In production, would fetch actual instrument token from Kite
        return {
            'tradingsymbol': tradingsymbol,
            'instrument_token': 0,  # Placeholder
            'strike': strike
        }

    async def _place_exit_order(
        self,
        strategy: AutoPilotStrategy,
        leg: AutoPilotPositionLeg,
        transaction_type: str,
        order_type: str,
        quantity: int,
        price: Optional[Decimal]
    ) -> Dict[str, Any]:
        """Place exit order via Kite."""
        # Placeholder - in production would use actual Kite API
        return {
            'order_id': f"order_{uuid.uuid4().hex[:8]}",
            'executed_price': leg.entry_price,  # Placeholder
            'status': 'complete'
        }

    async def _place_entry_order(
        self,
        strategy: AutoPilotStrategy,
        tradingsymbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: Optional[Decimal]
    ) -> Dict[str, Any]:
        """Place entry order via Kite."""
        # Placeholder - in production would use actual Kite API
        return {
            'order_id': f"order_{uuid.uuid4().hex[:8]}",
            'executed_price': Decimal('100'),  # Placeholder
            'status': 'complete'
        }

    def _get_lot_size(self, underlying: str) -> int:
        """Get lot size for underlying."""
        from app.constants import get_lot_size
        return get_lot_size(underlying)
