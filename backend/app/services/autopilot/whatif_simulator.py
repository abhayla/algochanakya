"""
What-If Simulator - Phase 5C

Simulates proposed adjustments and compares before/after scenarios.
Helps users make informed decisions by showing impact on P&L, Greeks, and risk metrics.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from copy import deepcopy
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from kiteconnect import KiteConnect

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPositionLeg,
    PositionLegStatus
)
from app.services.legacy.market_data import MarketDataService
from app.services.autopilot.position_leg_service import PositionLegService
from app.services.autopilot.strike_finder_service import StrikeFinderService
from app.services.options.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)


class WhatIfSimulator:
    """
    Simulates position adjustments and compares outcomes.

    Simulates:
    - Shift leg to new strike
    - Roll leg to new expiry
    - Break trade scenarios
    - Exit scenarios
    - Add hedge scenarios

    Provides:
    - Before/After comparison
    - P&L impact
    - Greeks changes
    - Breakeven shifts
    - Risk metrics
    """

    def __init__(
        self,
        kite: KiteConnect,
        db: AsyncSession,
        market_data: MarketDataService
    ):
        self.kite = kite
        self.db = db
        self.market_data = market_data
        self.position_leg_service = PositionLegService(kite, db)
        self.strike_finder = StrikeFinderService(kite, db)
        self.greeks_calculator = GreeksCalculatorService()

    async def simulate_shift(
        self,
        strategy_id: int,
        leg_id: str,
        target_strike: Optional[Decimal] = None,
        target_delta: Optional[Decimal] = None,
        shift_amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate shifting a leg to a new strike.

        Returns before/after comparison with impact metrics.
        """
        try:
            # Get current state
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)

            if not strategy or not leg:
                raise ValueError("Strategy or leg not found")

            # Get spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if not spot_price:
                raise ValueError("Cannot get spot price")

            # Calculate current state
            current_state = await self._calculate_current_state(strategy)

            # Determine new strike
            new_strike = target_strike
            if not new_strike:
                if target_delta:
                    # Find by delta
                    result = await self.strike_finder.find_strike_by_delta(
                        underlying=strategy.underlying,
                        expiry=leg.expiry,
                        option_type=leg.contract_type,
                        target_delta=target_delta,
                        prefer_round_strike=True
                    )
                    new_strike = result['strike']
                elif shift_amount:
                    # Shift by amount
                    new_strike = leg.strike + Decimal(str(shift_amount))

            if not new_strike:
                raise ValueError("Cannot determine new strike")

            # Get new strike details
            new_strike_data = await self.strike_finder.find_strike_by_premium(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                option_type=leg.contract_type,
                target_premium=Decimal('100'),  # Dummy, will get actual
                tolerance=Decimal('10000'),  # Wide tolerance
                prefer_round_strike=False
            )

            # Simulate new position
            new_state = await self._simulate_shift_scenario(
                strategy=strategy,
                old_leg=leg,
                new_strike=new_strike,
                new_strike_data=new_strike_data,
                spot_price=spot_price
            )

            # Calculate impact
            impact = self._calculate_impact(current_state, new_state)

            return {
                "simulation_type": "shift",
                "leg_id": leg_id,
                "current_strike": float(leg.strike),
                "new_strike": float(new_strike),
                "before": current_state,
                "after": new_state,
                "impact": impact,
                "recommendation": self._get_recommendation(impact),
                "simulated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error simulating shift: {e}")
            raise

    async def simulate_roll(
        self,
        strategy_id: int,
        leg_id: str,
        target_expiry: date,
        target_strike: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Simulate rolling a leg to new expiry.

        Returns before/after comparison with roll cost.
        """
        try:
            # Get current state
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)

            if not strategy or not leg:
                raise ValueError("Strategy or leg not found")

            # Get spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if not spot_price:
                raise ValueError("Cannot get spot price")

            # Calculate current state
            current_state = await self._calculate_current_state(strategy)

            # Use same strike if not specified
            new_strike = target_strike or leg.strike

            # Get new expiry option details
            # (In production, would fetch actual instrument details)
            new_option_premium = await self._estimate_new_expiry_premium(
                underlying=strategy.underlying,
                strike=new_strike,
                option_type=leg.contract_type,
                expiry=target_expiry,
                spot_price=spot_price
            )

            # Calculate roll cost
            exit_premium = float(leg.entry_price or 0)
            entry_premium = float(new_option_premium)
            roll_cost = (entry_premium - exit_premium) * leg.lots * self._get_lot_size(strategy.underlying)

            # Calculate DTE for new expiry
            new_dte = (target_expiry - date.today()).days

            # Simulate new position
            new_state = current_state.copy()
            new_state["dte"] = new_dte
            new_state["theta_decay_rate"] = "higher" if new_dte > 14 else "lower"
            new_state["gamma_risk"] = "lower" if new_dte > 14 else "higher"

            return {
                "simulation_type": "roll",
                "leg_id": leg_id,
                "current_expiry": leg.expiry.isoformat(),
                "new_expiry": target_expiry.isoformat(),
                "current_dte": (leg.expiry - date.today()).days,
                "new_dte": new_dte,
                "before": current_state,
                "after": new_state,
                "roll_cost": roll_cost,
                "exit_premium": exit_premium,
                "entry_premium": entry_premium,
                "recommendation": "Roll if cost is acceptable" if abs(roll_cost) < 1000 else "Roll cost is high, consider alternatives",
                "simulated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error simulating roll: {e}")
            raise

    async def simulate_break_trade(
        self,
        strategy_id: int,
        leg_id: str,
        premium_split: str = "equal",
        max_delta: Decimal = Decimal('0.30')
    ) -> Dict[str, Any]:
        """
        Simulate break/split trade on a losing leg.

        Returns detailed breakdown of exit cost, new positions, and recovery plan.
        """
        try:
            # Get current state
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            leg = await self.position_leg_service.get_position_leg(strategy_id, leg_id)

            if not strategy or not leg:
                raise ValueError("Strategy or leg not found")

            # Get current price
            if not leg.tradingsymbol:
                raise ValueError("Leg tradingsymbol not found")

            ltp_data = await self.market_data.get_ltp([f"NFO:{leg.tradingsymbol}"])
            current_ltp = ltp_data.get(f"NFO:{leg.tradingsymbol}")

            if not current_ltp:
                raise ValueError("Cannot get current price")

            # Calculate exit cost
            exit_cost = float(current_ltp)
            recovery_premium = exit_cost

            # Split recovery premium
            if premium_split == "equal":
                put_target = recovery_premium / 2
                call_target = recovery_premium / 2
            else:  # weighted
                put_target = recovery_premium / 2
                call_target = recovery_premium / 2

            # Find new strikes
            put_strike_data = await self.strike_finder.find_strike_by_premium(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                option_type="PE",
                target_premium=Decimal(str(put_target)),
                tolerance=Decimal('20'),
                prefer_round_strike=True
            )

            call_strike_data = await self.strike_finder.find_strike_by_premium(
                underlying=strategy.underlying,
                expiry=leg.expiry,
                option_type="CE",
                target_premium=Decimal(str(call_target)),
                tolerance=Decimal('20'),
                prefer_round_strike=True
            )

            # Calculate total recovery premium
            put_premium = float(put_strike_data.get('ltp', 0))
            call_premium = float(call_strike_data.get('ltp', 0))
            total_recovery = put_premium + call_premium

            # Net cost
            net_cost = exit_cost - total_recovery

            # Calculate current state
            current_state = await self._calculate_current_state(strategy)

            # Estimate new state (simplified)
            new_state = current_state.copy()
            new_state["num_positions"] = current_state.get("num_positions", 0) + 1  # -1 old, +2 new = +1 net
            new_state["unrealized_pnl"] = current_state.get("unrealized_pnl", 0) - net_cost

            return {
                "simulation_type": "break_trade",
                "leg_id": leg_id,
                "current_leg": {
                    "strike": float(leg.strike),
                    "type": leg.contract_type,
                    "current_price": exit_cost,
                    "entry_price": float(leg.entry_price or 0),
                    "unrealized_pnl": float(leg.unrealized_pnl or 0)
                },
                "exit_cost": exit_cost,
                "recovery_plan": {
                    "put_strike": float(put_strike_data['strike']),
                    "put_premium": put_premium,
                    "put_delta": float(put_strike_data.get('delta', 0)),
                    "call_strike": float(call_strike_data['strike']),
                    "call_premium": call_premium,
                    "call_delta": float(call_strike_data.get('delta', 0)),
                    "total_recovery": total_recovery
                },
                "net_cost": net_cost,
                "before": current_state,
                "after": new_state,
                "recommendation": (
                    "Execute break trade - good recovery potential"
                    if net_cost < exit_cost * 0.5
                    else "Break trade may not be optimal - recovery premium is low"
                ),
                "simulated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error simulating break trade: {e}")
            raise

    async def simulate_exit(
        self,
        strategy_id: int,
        exit_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Simulate exiting the position (partial or full).

        Returns impact of exit on realized P&L.
        """
        try:
            # Get current state
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            # Calculate current state
            current_state = await self._calculate_current_state(strategy)

            # Get position legs
            result = await self.db.execute(
                select(AutoPilotPositionLeg).where(
                    AutoPilotPositionLeg.strategy_id == strategy_id,
                    AutoPilotPositionLeg.status == PositionLegStatus.OPEN.value
                )
            )
            position_legs = result.scalars().all()

            # Calculate exit value
            total_exit_value = 0
            for leg in position_legs:
                if leg.tradingsymbol:
                    try:
                        ltp_data = await self.market_data.get_ltp([f"NFO:{leg.tradingsymbol}"])
                        current_ltp = ltp_data.get(f"NFO:{leg.tradingsymbol}", 0)
                        total_exit_value += float(current_ltp) * leg.lots * self._get_lot_size(strategy.underlying)
                    except:
                        pass

            # Realized P&L on exit
            runtime_state = strategy.runtime_state or {}
            current_unrealized_pnl = runtime_state.get('current_pnl', 0)
            realized_pnl_on_exit = current_unrealized_pnl

            return {
                "simulation_type": "exit",
                "exit_type": exit_type,
                "current_positions": len(position_legs),
                "before": current_state,
                "exit_impact": {
                    "total_exit_value": total_exit_value,
                    "realized_pnl": realized_pnl_on_exit,
                    "positions_closed": len(position_legs),
                    "capital_freed": "full margin released"
                },
                "after": {
                    "num_positions": 0,
                    "net_delta": 0,
                    "net_theta": 0,
                    "unrealized_pnl": 0,
                    "realized_pnl": realized_pnl_on_exit
                },
                "recommendation": (
                    "Exit recommended" if realized_pnl_on_exit < -1000
                    else "Hold for theta decay" if realized_pnl_on_exit > 0
                    else "Monitor and decide"
                ),
                "simulated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error simulating exit: {e}")
            raise

    async def compare_scenarios(
        self,
        strategy_id: int,
        scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare multiple adjustment scenarios side-by-side.

        Args:
            scenarios: List of scenario configs, e.g.:
                [
                    {"type": "shift", "leg_id": "leg1", "target_delta": 0.15},
                    {"type": "break", "leg_id": "leg1"},
                    {"type": "exit"}
                ]

        Returns:
            Side-by-side comparison with recommendations
        """
        try:
            results = []

            for scenario in scenarios:
                scenario_type = scenario.get("type")

                if scenario_type == "shift":
                    result = await self.simulate_shift(
                        strategy_id=strategy_id,
                        leg_id=scenario.get("leg_id"),
                        target_strike=scenario.get("target_strike"),
                        target_delta=scenario.get("target_delta"),
                        shift_amount=scenario.get("shift_amount")
                    )
                elif scenario_type == "roll":
                    result = await self.simulate_roll(
                        strategy_id=strategy_id,
                        leg_id=scenario.get("leg_id"),
                        target_expiry=scenario.get("target_expiry"),
                        target_strike=scenario.get("target_strike")
                    )
                elif scenario_type == "break":
                    result = await self.simulate_break_trade(
                        strategy_id=strategy_id,
                        leg_id=scenario.get("leg_id"),
                        premium_split=scenario.get("premium_split", "equal")
                    )
                elif scenario_type == "exit":
                    result = await self.simulate_exit(
                        strategy_id=strategy_id,
                        exit_type=scenario.get("exit_type", "full")
                    )
                else:
                    continue

                results.append(result)

            # Rank scenarios by impact
            ranked_scenarios = self._rank_scenarios(results)

            return {
                "strategy_id": strategy_id,
                "scenarios_compared": len(results),
                "results": results,
                "ranked": ranked_scenarios,
                "best_option": ranked_scenarios[0] if ranked_scenarios else None,
                "compared_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error comparing scenarios: {e}")
            raise

    async def _calculate_current_state(
        self,
        strategy: AutoPilotStrategy
    ) -> Dict[str, Any]:
        """Calculate current position state."""

        runtime_state = strategy.runtime_state or {}

        return {
            "net_delta": float(strategy.net_delta or 0),
            "net_theta": float(strategy.net_theta or 0),
            "net_gamma": float(strategy.net_gamma or 0),
            "net_vega": float(strategy.net_vega or 0),
            "unrealized_pnl": runtime_state.get('current_pnl', 0),
            "realized_pnl": runtime_state.get('realized_pnl', 0),
            "num_positions": len(runtime_state.get('current_positions', [])),
            "breakeven_lower": float(strategy.breakeven_lower) if strategy.breakeven_lower else None,
            "breakeven_upper": float(strategy.breakeven_upper) if strategy.breakeven_upper else None,
            "dte": strategy.dte or 0
        }

    async def _simulate_shift_scenario(
        self,
        strategy: AutoPilotStrategy,
        old_leg: AutoPilotPositionLeg,
        new_strike: Decimal,
        new_strike_data: Dict[str, Any],
        spot_price: Decimal
    ) -> Dict[str, Any]:
        """Simulate position after shifting a leg."""

        # Calculate delta change
        old_delta = float(old_leg.delta or 0)
        new_delta = float(new_strike_data.get('delta', 0))
        delta_change = new_delta - old_delta

        # Calculate new net delta
        current_net_delta = float(strategy.net_delta or 0)
        new_net_delta = current_net_delta + delta_change

        # Calculate premium change (shift cost)
        old_premium = float(old_leg.entry_price or 0)
        new_premium = float(new_strike_data.get('ltp', 0))
        shift_cost = (new_premium - old_premium) * old_leg.lots * self._get_lot_size(strategy.underlying)

        # New state
        runtime_state = strategy.runtime_state or {}
        current_pnl = runtime_state.get('current_pnl', 0)

        return {
            "net_delta": new_net_delta,
            "net_theta": float(strategy.net_theta or 0),  # Approximate
            "net_gamma": float(strategy.net_gamma or 0),
            "net_vega": float(strategy.net_vega or 0),
            "unrealized_pnl": current_pnl - shift_cost,
            "realized_pnl": runtime_state.get('realized_pnl', 0),
            "num_positions": len(runtime_state.get('current_positions', [])),
            "shift_cost": shift_cost,
            "delta_change": delta_change,
            "dte": strategy.dte or 0
        }

    def _calculate_impact(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate impact metrics between before/after states."""

        return {
            "delta_change": after["net_delta"] - before["net_delta"],
            "theta_change": after["net_theta"] - before["net_theta"],
            "pnl_change": after["unrealized_pnl"] - before["unrealized_pnl"],
            "cost": after.get("shift_cost", 0),
            "delta_reduction_pct": (
                abs(after["net_delta"]) / abs(before["net_delta"]) - 1
                if before["net_delta"] != 0 else 0
            ) * 100
        }

    def _get_recommendation(self, impact: Dict[str, Any]) -> str:
        """Get recommendation based on impact analysis."""

        cost = impact.get("cost", 0)
        delta_change = impact.get("delta_change", 0)
        delta_reduction_pct = impact.get("delta_reduction_pct", 0)

        if abs(cost) > 500:
            return "High cost adjustment - consider if delta reduction justifies the expense"
        elif abs(delta_reduction_pct) > 30:
            return "Good delta reduction - recommended if cost is acceptable"
        elif abs(delta_change) < 0.05:
            return "Minimal impact - adjustment may not be necessary"
        else:
            return "Moderate impact - evaluate based on risk tolerance"

    def _rank_scenarios(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank scenarios by effectiveness."""

        # Score each scenario
        scored = []
        for result in results:
            impact = result.get("impact", {})
            cost = abs(impact.get("cost", result.get("net_cost", 0)))
            delta_reduction = abs(impact.get("delta_reduction_pct", 0))
            pnl_improvement = impact.get("pnl_change", 0)

            # Simple scoring: lower cost + higher delta reduction + positive P&L = better
            score = delta_reduction / 10 - cost / 100 + pnl_improvement / 10

            scored.append({
                "scenario": result,
                "score": score
            })

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)

        return [s["scenario"] for s in scored]

    async def _estimate_new_expiry_premium(
        self,
        underlying: str,
        strike: Decimal,
        option_type: str,
        expiry: date,
        spot_price: Decimal
    ) -> Decimal:
        """Estimate premium for new expiry option."""

        # In production, would fetch actual market price
        # For now, use rough estimation based on DTE and moneyness

        dte = (expiry - date.today()).days
        moneyness = float(spot_price - strike) / float(spot_price)

        # Simple estimation
        base_premium = 100  # Base premium
        time_value = dte * 2  # ₹2 per day of time value
        intrinsic = max(0, float(spot_price - strike)) if option_type == "CE" else max(0, float(strike - spot_price))

        estimated_premium = intrinsic + time_value + base_premium

        return Decimal(str(estimated_premium))

    def _get_lot_size(self, underlying: str) -> int:
        """Get lot size for underlying."""
        from app.constants import get_lot_size
        return get_lot_size(underlying)
