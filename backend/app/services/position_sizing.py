"""
Position Sizing Service - Phase 3

Calculate optimal lot size based on risk parameters.

Inputs:
- Account capital
- Risk per trade (% or fixed amount)
- Max loss per strategy
- Current VIX (for volatility adjustment)

Logic:
1. Calculate max loss allowed based on risk parameters
2. Estimate max loss for the strategy configuration
3. Determine optimal lot size
4. Apply VIX-based adjustments if enabled
5. Ensure lot size is within min/max bounds
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal, ROUND_DOWN
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.autopilot import (
    PositionSizingRequest,
    PositionSizingResponse
)

logger = logging.getLogger(__name__)

# Lot sizes for different underlyings
LOT_SIZES = {
    'NIFTY': 25,
    'BANKNIFTY': 15,
    'FINNIFTY': 25,
    'SENSEX': 10,
    'MIDCPNIFTY': 75,
}

# Default lot size for unknown underlyings
DEFAULT_LOT_SIZE = 25

# VIX thresholds for position sizing adjustments
VIX_THRESHOLDS = {
    'low': 12,      # VIX below this = low volatility
    'normal': 18,   # VIX below this = normal volatility
    'high': 25,     # VIX below this = high volatility
    'extreme': 35   # VIX above this = extreme volatility
}

# Position size multipliers based on VIX regime
VIX_MULTIPLIERS = {
    'low': Decimal('1.25'),      # Can take slightly larger positions
    'normal': Decimal('1.0'),    # Normal position size
    'high': Decimal('0.75'),     # Reduce position size
    'extreme': Decimal('0.5'),   # Significantly reduce position size
    'crisis': Decimal('0.25')    # Minimal position size
}


class PositionSizingService:
    """
    Service for calculating optimal position sizes based on risk parameters.

    Position sizing is a critical risk management technique that ensures
    no single trade can cause catastrophic losses to the account.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def calculate_position_size(
        self,
        request: PositionSizingRequest
    ) -> PositionSizingResponse:
        """
        Calculate optimal position size for a strategy.

        Args:
            request: Position sizing request with account and strategy details

        Returns:
            PositionSizingResponse with calculated lots and risk metrics
        """
        underlying = request.underlying.upper()
        lot_size = LOT_SIZES.get(underlying, DEFAULT_LOT_SIZE)

        # Calculate max loss allowed
        max_loss_allowed = self._calculate_max_loss_allowed(
            account_capital=request.account_capital,
            risk_per_trade_pct=request.risk_per_trade_pct,
            risk_per_trade_amount=request.risk_per_trade_amount
        )

        # Estimate max loss for the strategy
        estimated_max_loss_per_lot = self._estimate_max_loss_per_lot(
            legs=request.legs,
            underlying=underlying,
            spot_price=request.spot_price
        )

        # Handle undefined risk strategies
        if estimated_max_loss_per_lot is None or estimated_max_loss_per_lot == Decimal('0'):
            # Undefined risk (naked positions)
            # Use a conservative estimate based on spot price
            estimated_max_loss_per_lot = request.spot_price * lot_size * Decimal('0.10')
            is_undefined_risk = True
        else:
            is_undefined_risk = False

        # Calculate base lots
        if estimated_max_loss_per_lot > 0:
            base_lots = int(max_loss_allowed / estimated_max_loss_per_lot)
        else:
            base_lots = 1

        # Apply VIX adjustment if provided
        vix_regime = None
        vix_multiplier = Decimal('1.0')

        if request.current_vix is not None:
            vix_regime = self._get_vix_regime(request.current_vix)
            vix_multiplier = VIX_MULTIPLIERS.get(vix_regime, Decimal('1.0'))

        # Calculate adjusted lots
        adjusted_lots = int(Decimal(str(base_lots)) * vix_multiplier)

        # Apply min/max constraints
        min_lots = request.min_lots or 1
        max_lots = request.max_lots

        final_lots = max(min_lots, adjusted_lots)
        if max_lots is not None:
            final_lots = min(final_lots, max_lots)

        # Calculate final quantities
        quantity = final_lots * lot_size

        # Calculate actual max loss
        actual_max_loss = estimated_max_loss_per_lot * final_lots if not is_undefined_risk else None

        # Calculate risk percentage
        risk_percentage = (actual_max_loss / request.account_capital * 100) if actual_max_loss else None

        # Build reasoning
        reasoning = self._build_reasoning(
            account_capital=request.account_capital,
            max_loss_allowed=max_loss_allowed,
            estimated_max_loss_per_lot=estimated_max_loss_per_lot,
            base_lots=base_lots,
            vix_regime=vix_regime,
            vix_multiplier=vix_multiplier,
            adjusted_lots=adjusted_lots,
            final_lots=final_lots,
            is_undefined_risk=is_undefined_risk,
            min_lots=min_lots,
            max_lots=max_lots
        )

        return PositionSizingResponse(
            recommended_lots=final_lots,
            recommended_quantity=quantity,
            lot_size=lot_size,
            max_loss_allowed=max_loss_allowed,
            estimated_max_loss=actual_max_loss,
            risk_percentage=risk_percentage,
            vix_adjustment_applied=vix_multiplier != Decimal('1.0'),
            vix_regime=vix_regime,
            is_undefined_risk=is_undefined_risk,
            reasoning=reasoning
        )

    def calculate_lots_for_capital(
        self,
        account_capital: Decimal,
        risk_per_trade_pct: Decimal,
        max_loss_per_lot: Decimal,
        current_vix: Optional[float] = None
    ) -> int:
        """
        Simple lot calculation for quick sizing.

        Args:
            account_capital: Total account capital
            risk_per_trade_pct: Maximum risk per trade as percentage
            max_loss_per_lot: Maximum loss per lot for the strategy
            current_vix: Optional VIX for adjustment

        Returns:
            Number of lots to trade
        """
        max_loss_allowed = account_capital * (risk_per_trade_pct / Decimal('100'))

        if max_loss_per_lot <= 0:
            return 1

        base_lots = int(max_loss_allowed / max_loss_per_lot)

        if current_vix is not None:
            vix_regime = self._get_vix_regime(current_vix)
            vix_multiplier = VIX_MULTIPLIERS.get(vix_regime, Decimal('1.0'))
            base_lots = int(Decimal(str(base_lots)) * vix_multiplier)

        return max(1, base_lots)

    def get_estimated_max_loss(
        self,
        legs: List[Dict[str, Any]],
        underlying: str,
        spot_price: Decimal
    ) -> Optional[Decimal]:
        """
        Estimate maximum loss for a strategy configuration.

        Args:
            legs: List of leg configurations
            underlying: Underlying symbol
            spot_price: Current spot price

        Returns:
            Estimated max loss per lot, or None for undefined risk
        """
        return self._estimate_max_loss_per_lot(legs, underlying, spot_price)

    def _calculate_max_loss_allowed(
        self,
        account_capital: Decimal,
        risk_per_trade_pct: Optional[Decimal],
        risk_per_trade_amount: Optional[Decimal]
    ) -> Decimal:
        """Calculate maximum loss allowed for a single trade."""
        if risk_per_trade_amount is not None:
            return risk_per_trade_amount

        if risk_per_trade_pct is not None:
            return account_capital * (risk_per_trade_pct / Decimal('100'))

        # Default to 2% risk
        return account_capital * Decimal('0.02')

    def _estimate_max_loss_per_lot(
        self,
        legs: List[Dict[str, Any]],
        underlying: str,
        spot_price: Decimal
    ) -> Optional[Decimal]:
        """
        Estimate max loss per lot based on strategy structure.

        Strategies with defined risk:
        - Credit spreads: Max loss = spread width - premium received
        - Debit spreads: Max loss = premium paid
        - Iron Condor: Max loss = spread width - net premium
        - Butterfly: Max loss = premium paid

        Strategies with undefined risk:
        - Naked calls/puts
        - Strangles/Straddles (short)

        Returns None for undefined risk strategies.
        """
        if not legs:
            return None

        lot_size = LOT_SIZES.get(underlying.upper(), DEFAULT_LOT_SIZE)

        # Categorize legs
        long_calls = []
        short_calls = []
        long_puts = []
        short_puts = []

        for leg in legs:
            action = leg.get('action', '').upper()
            option_type = leg.get('option_type', '').upper()
            strike = Decimal(str(leg.get('strike', 0)))
            premium = Decimal(str(leg.get('premium', 0)))

            leg_info = {
                'strike': strike,
                'premium': premium,
                'quantity': leg.get('quantity', 1)
            }

            if option_type == 'CE' or option_type == 'CALL':
                if action == 'BUY':
                    long_calls.append(leg_info)
                else:
                    short_calls.append(leg_info)
            elif option_type == 'PE' or option_type == 'PUT':
                if action == 'BUY':
                    long_puts.append(leg_info)
                else:
                    short_puts.append(leg_info)

        # Calculate net premium
        net_premium = Decimal('0')
        for leg in legs:
            action = leg.get('action', '').upper()
            premium = Decimal(str(leg.get('premium', 0)))
            qty = leg.get('quantity', 1)

            if action == 'BUY':
                net_premium -= premium * qty
            else:
                net_premium += premium * qty

        net_premium_per_lot = net_premium * lot_size

        # Detect strategy type and calculate max loss

        # 1. Credit Call Spread (short call + long call, short strike < long strike)
        if len(short_calls) == 1 and len(long_calls) == 1 and not short_puts and not long_puts:
            spread_width = abs(long_calls[0]['strike'] - short_calls[0]['strike'])
            max_loss = (spread_width - net_premium) * lot_size
            return max(Decimal('0'), max_loss)

        # 2. Credit Put Spread (short put + long put, short strike > long strike)
        if len(short_puts) == 1 and len(long_puts) == 1 and not short_calls and not long_calls:
            spread_width = abs(short_puts[0]['strike'] - long_puts[0]['strike'])
            max_loss = (spread_width - net_premium) * lot_size
            return max(Decimal('0'), max_loss)

        # 3. Debit Call Spread (long call + short call, long strike < short strike)
        if len(long_calls) == 1 and len(short_calls) == 1 and not short_puts and not long_puts:
            if long_calls[0]['strike'] < short_calls[0]['strike']:
                max_loss = abs(net_premium_per_lot)  # Premium paid
                return max_loss

        # 4. Debit Put Spread (long put + short put, long strike > short strike)
        if len(long_puts) == 1 and len(short_puts) == 1 and not short_calls and not long_calls:
            if long_puts[0]['strike'] > short_puts[0]['strike']:
                max_loss = abs(net_premium_per_lot)  # Premium paid
                return max_loss

        # 5. Iron Condor (credit call spread + credit put spread)
        if len(short_calls) == 1 and len(long_calls) == 1 and len(short_puts) == 1 and len(long_puts) == 1:
            call_spread_width = abs(long_calls[0]['strike'] - short_calls[0]['strike'])
            put_spread_width = abs(short_puts[0]['strike'] - long_puts[0]['strike'])
            max_spread_width = max(call_spread_width, put_spread_width)
            max_loss = (max_spread_width - net_premium) * lot_size
            return max(Decimal('0'), max_loss)

        # 6. Long Butterfly (CE or PE)
        if len(long_calls) == 2 and len(short_calls) == 1:
            # Long butterfly with calls
            max_loss = abs(net_premium_per_lot)
            return max_loss

        if len(long_puts) == 2 and len(short_puts) == 1:
            # Long butterfly with puts
            max_loss = abs(net_premium_per_lot)
            return max_loss

        # 7. Long Straddle/Strangle (buy call + buy put)
        if len(long_calls) == 1 and len(long_puts) == 1 and not short_calls and not short_puts:
            max_loss = abs(net_premium_per_lot)  # Premium paid
            return max_loss

        # 8. Naked short positions - undefined risk
        if (short_calls and not long_calls) or (short_puts and not long_puts):
            return None

        # 9. Short Straddle/Strangle - undefined risk
        if short_calls and short_puts and not long_calls and not long_puts:
            return None

        # Default: if net premium is negative (paid), that's max loss for defined risk
        if net_premium_per_lot < 0:
            return abs(net_premium_per_lot)

        # If net credit received but structure unclear, return None (undefined)
        return None

    def _get_vix_regime(self, vix: float) -> str:
        """Determine VIX regime based on current VIX level."""
        if vix < VIX_THRESHOLDS['low']:
            return 'low'
        elif vix < VIX_THRESHOLDS['normal']:
            return 'normal'
        elif vix < VIX_THRESHOLDS['high']:
            return 'high'
        elif vix < VIX_THRESHOLDS['extreme']:
            return 'extreme'
        else:
            return 'crisis'

    def _build_reasoning(
        self,
        account_capital: Decimal,
        max_loss_allowed: Decimal,
        estimated_max_loss_per_lot: Decimal,
        base_lots: int,
        vix_regime: Optional[str],
        vix_multiplier: Decimal,
        adjusted_lots: int,
        final_lots: int,
        is_undefined_risk: bool,
        min_lots: int,
        max_lots: Optional[int]
    ) -> List[str]:
        """Build human-readable reasoning for position size calculation."""
        reasoning = []

        reasoning.append(f"Account capital: ₹{account_capital:,.2f}")
        reasoning.append(f"Max loss allowed per trade: ₹{max_loss_allowed:,.2f}")

        if is_undefined_risk:
            reasoning.append("Strategy has undefined risk (naked positions or unclear structure)")
            reasoning.append(f"Using conservative estimate for max loss: ₹{estimated_max_loss_per_lot:,.2f} per lot")
        else:
            reasoning.append(f"Estimated max loss per lot: ₹{estimated_max_loss_per_lot:,.2f}")

        reasoning.append(f"Base lots calculated: {base_lots}")

        if vix_regime:
            reasoning.append(f"VIX regime: {vix_regime} (multiplier: {vix_multiplier})")
            if vix_multiplier != Decimal('1.0'):
                reasoning.append(f"VIX-adjusted lots: {adjusted_lots}")

        if final_lots != adjusted_lots:
            if final_lots == min_lots:
                reasoning.append(f"Applied minimum lots constraint: {min_lots}")
            elif max_lots and final_lots == max_lots:
                reasoning.append(f"Applied maximum lots constraint: {max_lots}")

        reasoning.append(f"Final recommended lots: {final_lots}")

        return reasoning


# Factory function for dependency injection
async def get_position_sizing_service(
    db: AsyncSession,
    user_id: UUID
) -> PositionSizingService:
    """Create a PositionSizingService instance"""
    return PositionSizingService(db, user_id)
