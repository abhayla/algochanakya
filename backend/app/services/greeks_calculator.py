"""
Greeks Calculator Service - Phase 3

Calculate option Greeks (Delta, Gamma, Theta, Vega) for positions.

Used for:
- Position risk assessment
- Delta-neutral hedging decisions
- Adjustment trigger conditions
- P&L projections

Greeks:
- Delta: Rate of change of option price with respect to underlying price
- Gamma: Rate of change of Delta with respect to underlying price
- Theta: Rate of change of option price with respect to time (time decay)
- Vega: Rate of change of option price with respect to volatility
- Rho: Rate of change of option price with respect to interest rate
"""
import logging
import math
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.autopilot import (
    GreeksSnapshot,
    PositionGreeksResponse
)

logger = logging.getLogger(__name__)

# Constants
TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365
RISK_FREE_RATE = 0.07  # 7% default risk-free rate (India)


class GreeksCalculatorService:
    """
    Service for calculating option Greeks using Black-Scholes model.

    Greeks help traders understand the risk exposure of their positions
    and make informed decisions about hedging and adjustments.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.risk_free_rate = RISK_FREE_RATE

    def set_risk_free_rate(self, rate: float):
        """Set the risk-free rate for calculations."""
        self.risk_free_rate = rate

    async def calculate_position_greeks(
        self,
        legs: List[Dict[str, Any]],
        spot_price: float,
        current_time: Optional[datetime] = None
    ) -> PositionGreeksResponse:
        """
        Calculate aggregate Greeks for all position legs.

        Args:
            legs: List of position legs with strike, expiry, option_type, quantity, iv
            spot_price: Current spot price of the underlying
            current_time: Current time (defaults to now)

        Returns:
            PositionGreeksResponse with aggregate and per-leg Greeks
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0

        leg_greeks = []

        for leg in legs:
            try:
                strike = float(leg.get('strike', 0))
                expiry = leg.get('expiry')
                option_type = leg.get('option_type', '').upper()
                quantity = int(leg.get('quantity', 1))
                iv = float(leg.get('iv', 0.20))  # Default 20% IV
                action = leg.get('action', '').upper()

                # Determine if CE or PE
                is_call = option_type in ('CE', 'CALL', 'C')

                # Calculate time to expiry
                time_to_expiry = self._calculate_time_to_expiry(expiry, current_time)

                if time_to_expiry <= 0:
                    # Expired option
                    leg_greeks.append({
                        'leg_index': len(leg_greeks),
                        'delta': 0,
                        'gamma': 0,
                        'theta': 0,
                        'vega': 0,
                        'rho': 0,
                        'expired': True
                    })
                    continue

                # Calculate Greeks for this leg
                greeks = self._calculate_greeks(
                    spot=spot_price,
                    strike=strike,
                    time_to_expiry=time_to_expiry,
                    volatility=iv,
                    is_call=is_call
                )

                # Adjust for position direction (buy = +, sell = -)
                multiplier = quantity if action == 'BUY' else -quantity

                leg_delta = greeks['delta'] * multiplier
                leg_gamma = greeks['gamma'] * abs(quantity)  # Gamma is always positive for long
                leg_theta = greeks['theta'] * multiplier
                leg_vega = greeks['vega'] * abs(quantity)  # Vega is always positive for long
                leg_rho = greeks['rho'] * multiplier

                total_delta += leg_delta
                total_gamma += leg_gamma if action == 'BUY' else -leg_gamma
                total_theta += leg_theta
                total_vega += leg_vega if action == 'BUY' else -leg_vega
                total_rho += leg_rho

                leg_greeks.append({
                    'leg_index': len(leg_greeks),
                    'strike': strike,
                    'option_type': option_type,
                    'action': action,
                    'quantity': quantity,
                    'delta': round(leg_delta, 4),
                    'gamma': round(leg_gamma if action == 'BUY' else -leg_gamma, 6),
                    'theta': round(leg_theta, 2),
                    'vega': round(leg_vega if action == 'BUY' else -leg_vega, 2),
                    'rho': round(leg_rho, 2),
                    'iv': round(iv * 100, 2),  # As percentage
                    'expired': False
                })

            except Exception as e:
                logger.error(f"Error calculating Greeks for leg: {e}")
                leg_greeks.append({
                    'leg_index': len(leg_greeks),
                    'error': str(e)
                })

        return PositionGreeksResponse(
            total_delta=round(total_delta, 4),
            total_gamma=round(total_gamma, 6),
            total_theta=round(total_theta, 2),
            total_vega=round(total_vega, 2),
            total_rho=round(total_rho, 2),
            spot_price=spot_price,
            calculated_at=current_time,
            leg_greeks=leg_greeks
        )

    def calculate_greeks_snapshot(
        self,
        legs: List[Dict[str, Any]],
        spot_price: float,
        current_time: Optional[datetime] = None
    ) -> GreeksSnapshot:
        """
        Calculate a quick snapshot of aggregate Greeks.

        Args:
            legs: List of position legs
            spot_price: Current spot price
            current_time: Current time

        Returns:
            GreeksSnapshot with aggregate values
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for leg in legs:
            try:
                strike = float(leg.get('strike', 0))
                expiry = leg.get('expiry')
                option_type = leg.get('option_type', '').upper()
                quantity = int(leg.get('quantity', 1))
                iv = float(leg.get('iv', 0.20))
                action = leg.get('action', '').upper()

                is_call = option_type in ('CE', 'CALL', 'C')
                time_to_expiry = self._calculate_time_to_expiry(expiry, current_time)

                if time_to_expiry <= 0:
                    continue

                greeks = self._calculate_greeks(
                    spot=spot_price,
                    strike=strike,
                    time_to_expiry=time_to_expiry,
                    volatility=iv,
                    is_call=is_call
                )

                multiplier = quantity if action == 'BUY' else -quantity

                total_delta += greeks['delta'] * multiplier
                total_gamma += greeks['gamma'] * (quantity if action == 'BUY' else -quantity)
                total_theta += greeks['theta'] * multiplier
                total_vega += greeks['vega'] * (quantity if action == 'BUY' else -quantity)

            except Exception as e:
                logger.error(f"Error in snapshot calculation: {e}")
                continue

        return GreeksSnapshot(
            delta=Decimal(str(round(total_delta, 4))),
            gamma=Decimal(str(round(total_gamma, 6))),
            theta=Decimal(str(round(total_theta, 2))),
            vega=Decimal(str(round(total_vega, 2))),
            spot_price=Decimal(str(spot_price)),
            calculated_at=current_time
        )

    def calculate_delta_hedge_quantity(
        self,
        current_delta: float,
        target_delta: float,
        spot_price: float,
        lot_size: int
    ) -> Dict[str, Any]:
        """
        Calculate the quantity of underlying needed to delta hedge.

        Args:
            current_delta: Current position delta
            target_delta: Target delta (usually 0 for delta-neutral)
            spot_price: Current spot price
            lot_size: Lot size for the underlying

        Returns:
            Dict with hedge direction, quantity, and estimated cost
        """
        delta_difference = target_delta - current_delta

        if abs(delta_difference) < 0.01:
            return {
                'action_needed': False,
                'reason': 'Position is already delta-neutral'
            }

        # Each underlying share has delta of 1
        # For index options, we hedge with futures
        shares_needed = delta_difference * lot_size

        # Round to nearest lot
        lots_needed = round(shares_needed / lot_size)
        quantity_needed = lots_needed * lot_size

        if lots_needed == 0:
            return {
                'action_needed': False,
                'reason': 'Delta difference too small to hedge'
            }

        action = 'BUY' if lots_needed > 0 else 'SELL'
        estimated_cost = abs(quantity_needed) * spot_price

        return {
            'action_needed': True,
            'action': action,
            'lots': abs(lots_needed),
            'quantity': abs(quantity_needed),
            'estimated_cost': round(estimated_cost, 2),
            'current_delta': round(current_delta, 4),
            'target_delta': round(target_delta, 4),
            'delta_after_hedge': round(target_delta, 4)
        }

    def calculate_option_price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool
    ) -> float:
        """
        Calculate theoretical option price using Black-Scholes.

        Args:
            spot: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (as decimal, e.g., 0.20 for 20%)
            is_call: True for call, False for put

        Returns:
            Theoretical option price
        """
        if time_to_expiry <= 0:
            # Expired - return intrinsic value
            if is_call:
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)

        d1, d2 = self._calculate_d1_d2(spot, strike, time_to_expiry, volatility)

        if is_call:
            price = spot * self._norm_cdf(d1) - strike * math.exp(-self.risk_free_rate * time_to_expiry) * self._norm_cdf(d2)
        else:
            price = strike * math.exp(-self.risk_free_rate * time_to_expiry) * self._norm_cdf(-d2) - spot * self._norm_cdf(-d1)

        return max(0, price)

    def _calculate_greeks(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool
    ) -> Dict[str, float]:
        """
        Calculate all Greeks for a single option.

        Returns:
            Dict with delta, gamma, theta, vega, rho
        """
        if time_to_expiry <= 0 or volatility <= 0:
            # Handle expired or zero volatility
            if is_call:
                delta = 1.0 if spot > strike else 0.0
            else:
                delta = -1.0 if spot < strike else 0.0

            return {
                'delta': delta,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }

        d1, d2 = self._calculate_d1_d2(spot, strike, time_to_expiry, volatility)
        sqrt_t = math.sqrt(time_to_expiry)
        discount = math.exp(-self.risk_free_rate * time_to_expiry)

        # Delta
        if is_call:
            delta = self._norm_cdf(d1)
        else:
            delta = self._norm_cdf(d1) - 1

        # Gamma (same for calls and puts)
        gamma = self._norm_pdf(d1) / (spot * volatility * sqrt_t)

        # Theta (per day)
        theta_common = -(spot * volatility * self._norm_pdf(d1)) / (2 * sqrt_t)

        if is_call:
            theta = theta_common - self.risk_free_rate * strike * discount * self._norm_cdf(d2)
        else:
            theta = theta_common + self.risk_free_rate * strike * discount * self._norm_cdf(-d2)

        # Convert to daily theta
        theta = theta / CALENDAR_DAYS_PER_YEAR

        # Vega (per 1% change in volatility)
        vega = spot * sqrt_t * self._norm_pdf(d1) / 100

        # Rho (per 1% change in interest rate)
        if is_call:
            rho = strike * time_to_expiry * discount * self._norm_cdf(d2) / 100
        else:
            rho = -strike * time_to_expiry * discount * self._norm_cdf(-d2) / 100

        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }

    def _calculate_d1_d2(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float
    ) -> Tuple[float, float]:
        """Calculate d1 and d2 for Black-Scholes formula."""
        sqrt_t = math.sqrt(time_to_expiry)
        d1 = (math.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * sqrt_t)
        d2 = d1 - volatility * sqrt_t
        return d1, d2

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

    def _calculate_time_to_expiry(
        self,
        expiry: Any,
        current_time: datetime
    ) -> float:
        """
        Calculate time to expiry in years.

        Args:
            expiry: Expiry date (can be date, datetime, or string)
            current_time: Current datetime

        Returns:
            Time to expiry in years (fraction)
        """
        try:
            if isinstance(expiry, str):
                # Parse string format (YYYY-MM-DD or DD-MMM-YYYY)
                for fmt in ['%Y-%m-%d', '%d-%b-%Y', '%d-%B-%Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        expiry_dt = datetime.strptime(expiry, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # Try parsing as date
                    expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            elif isinstance(expiry, date) and not isinstance(expiry, datetime):
                expiry_dt = datetime.combine(expiry, datetime.min.time())
            elif isinstance(expiry, datetime):
                expiry_dt = expiry
            else:
                logger.warning(f"Unknown expiry format: {type(expiry)}")
                return 0.0

            # Make expiry timezone-aware if needed
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

            # Make current_time timezone-aware if needed
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)

            # Calculate difference in days
            delta = expiry_dt - current_time
            days_to_expiry = delta.total_seconds() / (24 * 3600)

            # Convert to years (using calendar days)
            return max(0, days_to_expiry / CALENDAR_DAYS_PER_YEAR)

        except Exception as e:
            logger.error(f"Error calculating time to expiry: {e}")
            return 0.0

    def estimate_pnl_for_spot_change(
        self,
        current_delta: float,
        current_gamma: float,
        spot_change: float,
        lot_size: int
    ) -> float:
        """
        Estimate P&L for a given spot price change using delta-gamma approximation.

        P&L ≈ Delta × ΔS + 0.5 × Gamma × (ΔS)²

        Args:
            current_delta: Current position delta
            current_gamma: Current position gamma
            spot_change: Expected spot price change
            lot_size: Lot size for scaling

        Returns:
            Estimated P&L
        """
        delta_pnl = current_delta * spot_change * lot_size
        gamma_pnl = 0.5 * current_gamma * (spot_change ** 2) * lot_size

        return delta_pnl + gamma_pnl

    def calculate_iv_from_price(
        self,
        option_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool,
        max_iterations: int = 100,
        tolerance: float = 0.0001
    ) -> Optional[float]:
        """
        Calculate implied volatility from option price using Newton-Raphson method.

        Args:
            option_price: Observed option price
            spot: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            is_call: True for call, False for put
            max_iterations: Maximum iterations for Newton-Raphson
            tolerance: Convergence tolerance

        Returns:
            Implied volatility as decimal, or None if not converged
        """
        if time_to_expiry <= 0:
            return None

        # Initial guess
        iv = 0.20

        for _ in range(max_iterations):
            price = self.calculate_option_price(spot, strike, time_to_expiry, iv, is_call)
            diff = price - option_price

            if abs(diff) < tolerance:
                return iv

            # Calculate vega for Newton-Raphson
            d1, _ = self._calculate_d1_d2(spot, strike, time_to_expiry, iv)
            vega = spot * math.sqrt(time_to_expiry) * self._norm_pdf(d1)

            if vega < 0.0001:
                # Vega too small, can't converge
                break

            # Newton-Raphson update
            iv = iv - diff / vega

            # Keep IV in reasonable bounds
            iv = max(0.01, min(5.0, iv))

        return None


# Factory function for dependency injection
async def get_greeks_calculator_service(
    db: AsyncSession,
    user_id: UUID
) -> GreeksCalculatorService:
    """Create a GreeksCalculatorService instance"""
    return GreeksCalculatorService(db, user_id)
