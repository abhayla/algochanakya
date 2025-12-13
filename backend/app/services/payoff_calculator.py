"""
Payoff Calculator - Phase 5C

Calculates P/L diagrams, breakevens, and risk metrics for AutoPilot positions.
Provides data for payoff charts and position analysis.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPositionLeg,
    PositionLegStatus
)
from app.services.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)


@dataclass
class PayoffDataPoint:
    """Single data point in payoff chart."""
    spot_price: float
    pnl: float
    delta: Optional[float] = None
    is_breakeven: bool = False
    is_current: bool = False
    zone: str = "neutral"  # profit, loss, neutral


@dataclass
class PayoffMetrics:
    """Payoff analysis metrics."""
    max_profit: float
    max_loss: float
    max_profit_price: Optional[float]
    max_loss_price: Optional[float]
    breakeven_points: List[float]
    risk_reward_ratio: Optional[float]
    probability_profit: Optional[float]
    current_pnl: float
    net_credit: bool


class PayoffCalculator:
    """
    Calculate payoff diagrams and risk metrics for AutoPilot positions.

    Features:
    - P/L at expiry and current (with Greeks)
    - Breakeven point calculation
    - Max profit/loss zones
    - Risk/reward ratio
    - Payoff chart data points
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.greeks_calculator = GreeksCalculatorService()

    async def calculate_payoff(
        self,
        strategy_id: int,
        mode: str = "expiry",
        spot_range_pct: float = 10.0,
        num_points: int = 100
    ) -> Dict[str, Any]:
        """
        Calculate complete payoff analysis.

        Args:
            strategy_id: Strategy ID
            mode: "expiry" or "current" (with time value)
            spot_range_pct: % range around current spot (default: ±10%)
            num_points: Number of data points to calculate

        Returns:
            Complete payoff analysis with chart data and metrics
        """
        try:
            # Get strategy and legs
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            result = await self.db.execute(
                select(AutoPilotPositionLeg).where(
                    AutoPilotPositionLeg.strategy_id == strategy_id,
                    AutoPilotPositionLeg.status == PositionLegStatus.OPEN.value
                )
            )
            position_legs = result.scalars().all()

            if not position_legs:
                raise ValueError("No open position legs found")

            # Get current spot price from strategy or estimate
            runtime_state = strategy.runtime_state or {}
            current_spot = self._estimate_current_spot(position_legs)

            # Calculate spot price range
            spot_min = current_spot * (1 - spot_range_pct / 100)
            spot_max = current_spot * (1 + spot_range_pct / 100)
            spot_step = (spot_max - spot_min) / (num_points - 1)

            # Generate payoff data points
            payoff_data = []
            for i in range(num_points):
                spot = spot_min + (i * spot_step)

                if mode == "expiry":
                    pnl = self._calculate_pnl_at_expiry(position_legs, spot)
                else:  # current
                    pnl = await self._calculate_pnl_current(position_legs, spot, strategy)

                is_current = abs(spot - current_spot) < spot_step / 2

                payoff_data.append(PayoffDataPoint(
                    spot_price=spot,
                    pnl=pnl,
                    is_current=is_current,
                    zone="profit" if pnl > 0 else "loss" if pnl < 0 else "neutral"
                ))

            # Calculate metrics
            metrics = self._calculate_metrics(
                payoff_data=payoff_data,
                position_legs=position_legs,
                current_spot=current_spot
            )

            # Mark breakeven points in data
            for point in payoff_data:
                for be in metrics.breakeven_points:
                    if abs(point.spot_price - be) < spot_step:
                        point.is_breakeven = True

            return {
                "strategy_id": strategy_id,
                "mode": mode,
                "underlying": strategy.underlying,
                "current_spot": current_spot,
                "spot_range": {
                    "min": spot_min,
                    "max": spot_max,
                    "current": current_spot
                },
                "payoff_data": [
                    {
                        "spot_price": p.spot_price,
                        "pnl": p.pnl,
                        "is_breakeven": p.is_breakeven,
                        "is_current": p.is_current,
                        "zone": p.zone
                    }
                    for p in payoff_data
                ],
                "metrics": {
                    "max_profit": metrics.max_profit,
                    "max_loss": metrics.max_loss,
                    "max_profit_price": metrics.max_profit_price,
                    "max_loss_price": metrics.max_loss_price,
                    "breakeven_points": metrics.breakeven_points,
                    "risk_reward_ratio": metrics.risk_reward_ratio,
                    "probability_profit": metrics.probability_profit,
                    "current_pnl": metrics.current_pnl,
                    "net_credit": metrics.net_credit
                },
                "legs_summary": [
                    {
                        "leg_id": leg.leg_id,
                        "strike": float(leg.strike),
                        "type": leg.contract_type,
                        "action": leg.action,
                        "lots": leg.lots,
                        "entry_price": float(leg.entry_price or 0),
                        "current_price": float(leg.current_price or 0),
                        "unrealized_pnl": float(leg.unrealized_pnl or 0)
                    }
                    for leg in position_legs
                ],
                "calculated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating payoff for strategy {strategy_id}: {e}")
            raise

    def _calculate_pnl_at_expiry(
        self,
        position_legs: List[AutoPilotPositionLeg],
        spot_price: float
    ) -> float:
        """
        Calculate P/L at expiry (intrinsic value only).

        Formula:
        - CALL: max(0, spot - strike) for long, -max(0, spot - strike) for short
        - PUT: max(0, strike - spot) for long, -max(0, strike - spot) for short
        """
        total_pnl = 0

        for leg in position_legs:
            strike = float(leg.strike)
            entry_premium = float(leg.entry_price or 0)
            lot_size = self._get_lot_size(leg)

            # Calculate intrinsic value at expiry
            if leg.contract_type == "CE":
                intrinsic = max(0, spot_price - strike)
            else:  # PE
                intrinsic = max(0, strike - spot_price)

            # P/L per lot
            if leg.action == "BUY":
                pnl_per_lot = intrinsic - entry_premium
            else:  # SELL
                pnl_per_lot = entry_premium - intrinsic

            # Total P/L for all lots
            pnl = pnl_per_lot * leg.lots * lot_size
            total_pnl += pnl

        return total_pnl

    async def _calculate_pnl_current(
        self,
        position_legs: List[AutoPilotPositionLeg],
        spot_price: float,
        strategy: AutoPilotStrategy
    ) -> float:
        """
        Calculate P/L at current time (with time value using Greeks).

        Uses Black-Scholes to estimate current option prices.
        """
        total_pnl = 0

        for leg in position_legs:
            if not leg.expiry:
                continue

            # Calculate DTE
            dte = (leg.expiry - date.today()).days
            if dte < 0:
                dte = 0

            # Get current option price estimate using Greeks
            current_price = self._estimate_current_price(
                strike=float(leg.strike),
                spot=spot_price,
                dte=dte,
                option_type=leg.contract_type,
                iv=float(leg.iv or 0.20)  # Use leg IV or default
            )

            entry_premium = float(leg.entry_price or 0)
            lot_size = self._get_lot_size(leg)

            # P/L calculation
            if leg.action == "BUY":
                pnl_per_lot = current_price - entry_premium
            else:  # SELL
                pnl_per_lot = entry_premium - current_price

            pnl = pnl_per_lot * leg.lots * lot_size
            total_pnl += pnl

        return total_pnl

    def _estimate_current_price(
        self,
        strike: float,
        spot: float,
        dte: int,
        option_type: str,
        iv: float
    ) -> float:
        """
        Estimate current option price using simplified Black-Scholes.

        For quick payoff calculation without full Black-Scholes.
        """
        # Intrinsic value
        if option_type == "CE":
            intrinsic = max(0, spot - strike)
        else:  # PE
            intrinsic = max(0, strike - spot)

        # Time value (simplified)
        # TV decreases with DTE and moneyness
        moneyness = abs(spot - strike) / spot
        time_factor = dte / 365.0

        # Simple time value estimation
        time_value = (
            iv * spot * (time_factor ** 0.5) * (1 - moneyness)
        )

        # Total price
        current_price = intrinsic + max(0, time_value)

        return current_price

    def _calculate_metrics(
        self,
        payoff_data: List[PayoffDataPoint],
        position_legs: List[AutoPilotPositionLeg],
        current_spot: float
    ) -> PayoffMetrics:
        """Calculate payoff metrics from data points."""

        if not payoff_data:
            return PayoffMetrics(
                max_profit=0,
                max_loss=0,
                max_profit_price=None,
                max_loss_price=None,
                breakeven_points=[],
                risk_reward_ratio=None,
                probability_profit=None,
                current_pnl=0,
                net_credit=False
            )

        # Find max profit and max loss
        max_profit_point = max(payoff_data, key=lambda p: p.pnl)
        min_profit_point = min(payoff_data, key=lambda p: p.pnl)

        max_profit = max_profit_point.pnl
        max_loss = min_profit_point.pnl
        max_profit_price = max_profit_point.spot_price
        max_loss_price = min_profit_point.spot_price

        # Find breakeven points (where P&L crosses zero)
        breakeven_points = []
        for i in range(len(payoff_data) - 1):
            p1 = payoff_data[i]
            p2 = payoff_data[i + 1]

            # Check if P&L crosses zero
            if (p1.pnl >= 0 and p2.pnl < 0) or (p1.pnl < 0 and p2.pnl >= 0):
                # Linear interpolation to find exact breakeven
                if abs(p2.pnl - p1.pnl) > 0.01:
                    breakeven = p1.spot_price + (
                        (0 - p1.pnl) / (p2.pnl - p1.pnl) * (p2.spot_price - p1.spot_price)
                    )
                    breakeven_points.append(breakeven)

        # Calculate risk/reward ratio
        risk_reward_ratio = None
        if abs(max_loss) > 0:
            risk_reward_ratio = abs(max_profit / max_loss)

        # Calculate probability of profit (simplified)
        # % of spot prices that result in profit
        profit_points = sum(1 for p in payoff_data if p.pnl > 0)
        probability_profit = (profit_points / len(payoff_data)) * 100 if payoff_data else None

        # Current P&L
        current_pnl = next((p.pnl for p in payoff_data if p.is_current), 0)

        # Net credit or debit
        total_premium = sum(
            float(leg.entry_price or 0) * leg.lots * self._get_lot_size(leg) *
            (1 if leg.action == "SELL" else -1)
            for leg in position_legs
        )
        net_credit = total_premium > 0

        return PayoffMetrics(
            max_profit=max_profit,
            max_loss=max_loss,
            max_profit_price=max_profit_price,
            max_loss_price=max_loss_price,
            breakeven_points=sorted(breakeven_points),
            risk_reward_ratio=risk_reward_ratio,
            probability_profit=probability_profit,
            current_pnl=current_pnl,
            net_credit=net_credit
        )

    def _estimate_current_spot(self, position_legs: List[AutoPilotPositionLeg]) -> float:
        """Estimate current spot price from position legs."""

        if not position_legs:
            return 25000.0  # Default NIFTY price

        # Use average of strikes as rough estimate of ATM
        strikes = [float(leg.strike) for leg in position_legs if leg.strike]
        if strikes:
            return sum(strikes) / len(strikes)

        return 25000.0

    def _get_lot_size(self, leg: AutoPilotPositionLeg) -> int:
        """Get lot size from leg or default."""

        # Infer from tradingsymbol or use defaults
        if leg.tradingsymbol:
            if "NIFTY" in leg.tradingsymbol and "BANK" not in leg.tradingsymbol:
                return 25
            elif "BANKNIFTY" in leg.tradingsymbol:
                return 15
            elif "FINNIFTY" in leg.tradingsymbol:
                return 25
            elif "SENSEX" in leg.tradingsymbol:
                return 10

        return 25  # Default


async def calculate_breakevens(
    strategy_id: int,
    db: AsyncSession
) -> List[float]:
    """
    Calculate breakeven points for a strategy.

    Standalone function for quick breakeven calculation.
    """
    calculator = PayoffCalculator(db)

    try:
        payoff = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode="expiry",
            num_points=200  # More points for accuracy
        )

        return payoff["metrics"]["breakeven_points"]

    except Exception as e:
        logger.error(f"Error calculating breakevens for strategy {strategy_id}: {e}")
        return []


async def calculate_max_risk_reward(
    strategy_id: int,
    db: AsyncSession
) -> Dict[str, float]:
    """
    Calculate max risk and max reward for a strategy.

    Standalone function for risk/reward analysis.
    """
    calculator = PayoffCalculator(db)

    try:
        payoff = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode="expiry"
        )

        metrics = payoff["metrics"]

        return {
            "max_profit": metrics["max_profit"],
            "max_loss": metrics["max_loss"],
            "risk_reward_ratio": metrics["risk_reward_ratio"],
            "breakevens": metrics["breakeven_points"]
        }

    except Exception as e:
        logger.error(f"Error calculating risk/reward for strategy {strategy_id}: {e}")
        return {
            "max_profit": 0,
            "max_loss": 0,
            "risk_reward_ratio": None,
            "breakevens": []
        }
