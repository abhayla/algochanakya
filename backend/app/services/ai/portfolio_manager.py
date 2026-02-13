"""
Multi-Strategy Portfolio Manager

Manages multiple concurrent AutoPilot strategies with portfolio-level
Greeks tracking, risk management, correlation analysis, and capital allocation.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.autopilot import AutoPilotStrategy, AutoPilotPositionLeg
from app.services.options.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)


@dataclass
class PortfolioGreeks:
    """Aggregated portfolio Greeks"""
    total_delta: Decimal
    total_gamma: Decimal
    total_theta: Decimal
    total_vega: Decimal

    # Risk metrics
    delta_exposure: Decimal  # Total delta in rupees
    gamma_risk: Decimal      # Gamma risk measure
    theta_decay: Decimal     # Daily theta decay
    vega_exposure: Decimal   # IV exposure

    # Strategy breakdown
    strategy_greeks: Dict[int, Dict]  # {strategy_id: greeks}


@dataclass
class StrategyCorrelation:
    """Correlation between two strategies"""
    strategy1_id: int
    strategy2_id: int
    strategy1_name: str
    strategy2_name: str
    correlation: float  # -1.0 to 1.0
    diversification_benefit: float  # 0.0 to 1.0 (higher is better)


@dataclass
class PortfolioRebalance:
    """Portfolio rebalancing recommendation"""
    action: str  # REDUCE, INCREASE, CLOSE, OPEN
    strategy_id: int
    strategy_name: str
    current_allocation: Decimal
    recommended_allocation: Decimal
    reason: str
    priority: int  # 1 (high) to 3 (low)


@dataclass
class PortfolioSummary:
    """Complete portfolio overview"""
    total_strategies: int
    active_strategies: int
    total_capital_deployed: Decimal
    available_capital: Decimal

    total_pnl: Decimal
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal

    portfolio_greeks: PortfolioGreeks
    risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    risk_score: float  # 0-100

    strategy_summary: List[Dict]
    correlations: List[StrategyCorrelation]
    rebalance_recommendations: List[PortfolioRebalance]


class PortfolioManager:
    """
    Portfolio-level management for multiple concurrent AutoPilot strategies.

    Provides aggregated Greeks, correlation analysis, risk monitoring,
    and capital allocation recommendations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.greeks_calc = GreeksCalculatorService()

        # Risk thresholds
        self.MAX_PORTFOLIO_DELTA = 10000  # Max absolute delta in rupees
        self.MAX_PORTFOLIO_GAMMA = 500    # Max gamma exposure
        self.MAX_STRATEGY_CORRELATION = 0.7  # Max correlation between strategies
        self.MAX_CONCENTRATION = 0.40  # Max 40% in single strategy

    async def get_portfolio_summary(
        self,
        user_id,
        total_capital: Decimal
    ) -> PortfolioSummary:
        """
        Get complete portfolio overview with all metrics.

        Args:
            user_id: User UUID
            total_capital: Total available capital for trading

        Returns:
            PortfolioSummary with all portfolio-level metrics
        """
        # Get all active strategies
        query = select(AutoPilotStrategy).where(
            and_(
                AutoPilotStrategy.user_id == user_id,
                AutoPilotStrategy.status.in_(["ACTIVE", "MONITORING"])
            )
        )
        result = await self.db.execute(query)
        strategies = result.scalars().all()

        if not strategies:
            return self._empty_portfolio_summary(total_capital)

        # Calculate portfolio Greeks
        portfolio_greeks = await self._calculate_portfolio_greeks(strategies)

        # Calculate strategy summary
        strategy_summary = await self._get_strategy_summary(strategies)

        # Calculate capital deployment
        capital_deployed = sum(s.get("capital_used", Decimal("0")) for s in strategy_summary)
        available_capital = total_capital - capital_deployed

        # Calculate P&L
        total_pnl = sum(s.get("pnl", Decimal("0")) for s in strategy_summary)
        total_realized = sum(s.get("realized_pnl", Decimal("0")) for s in strategy_summary)
        total_unrealized = sum(s.get("unrealized_pnl", Decimal("0")) for s in strategy_summary)

        # Correlation analysis
        correlations = await self._calculate_correlations(strategies)

        # Risk assessment
        risk_level, risk_score = self._assess_portfolio_risk(
            portfolio_greeks, capital_deployed, total_capital, correlations
        )

        # Rebalancing recommendations
        rebalance_recs = await self._generate_rebalance_recommendations(
            strategies, strategy_summary, portfolio_greeks, total_capital, correlations
        )

        return PortfolioSummary(
            total_strategies=len(strategies),
            active_strategies=len([s for s in strategies if s.status == "ACTIVE"]),
            total_capital_deployed=capital_deployed,
            available_capital=available_capital,
            total_pnl=total_pnl,
            total_realized_pnl=total_realized,
            total_unrealized_pnl=total_unrealized,
            portfolio_greeks=portfolio_greeks,
            risk_level=risk_level,
            risk_score=risk_score,
            strategy_summary=strategy_summary,
            correlations=correlations,
            rebalance_recommendations=rebalance_recs
        )

    async def _calculate_portfolio_greeks(
        self,
        strategies: List[AutoPilotStrategy]
    ) -> PortfolioGreeks:
        """Calculate aggregated portfolio Greeks"""

        total_delta = Decimal("0")
        total_gamma = Decimal("0")
        total_theta = Decimal("0")
        total_vega = Decimal("0")

        strategy_greeks = {}

        for strategy in strategies:
            # Get position legs for this strategy
            legs_query = select(AutoPilotPositionLeg).where(
                AutoPilotPositionLeg.strategy_id == strategy.id
            )
            legs_result = await self.db.execute(legs_query)
            legs = legs_result.scalars().all()

            if not legs:
                continue

            # Sum Greeks for this strategy
            strategy_delta = sum(leg.delta or Decimal("0") for leg in legs)
            strategy_gamma = sum(leg.gamma or Decimal("0") for leg in legs)
            strategy_theta = sum(leg.theta or Decimal("0") for leg in legs)
            strategy_vega = sum(leg.vega or Decimal("0") for leg in legs)

            strategy_greeks[strategy.id] = {
                "delta": strategy_delta,
                "gamma": strategy_gamma,
                "theta": strategy_theta,
                "vega": strategy_vega
            }

            total_delta += strategy_delta
            total_gamma += strategy_gamma
            total_theta += strategy_theta
            total_vega += strategy_vega

        # Calculate risk metrics (simplified)
        delta_exposure = total_delta * Decimal("100")  # Delta × lot size
        gamma_risk = total_gamma * Decimal("100")
        theta_decay = total_theta * Decimal("100")
        vega_exposure = total_vega * Decimal("100")

        return PortfolioGreeks(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            delta_exposure=delta_exposure,
            gamma_risk=gamma_risk,
            theta_decay=theta_decay,
            vega_exposure=vega_exposure,
            strategy_greeks=strategy_greeks
        )

    async def _get_strategy_summary(
        self,
        strategies: List[AutoPilotStrategy]
    ) -> List[Dict]:
        """Get summary for each strategy"""

        summary = []

        for strategy in strategies:
            summary.append({
                "id": strategy.id,
                "name": strategy.name,
                "status": strategy.status,
                "underlying": strategy.underlying,
                "capital_used": strategy.max_capital or Decimal("0"),
                "pnl": strategy.total_pnl or Decimal("0"),
                "realized_pnl": strategy.realized_pnl or Decimal("0"),
                "unrealized_pnl": strategy.unrealized_pnl or Decimal("0"),
                "trades_count": strategy.total_trades or 0,
                "win_rate": float(strategy.win_rate or 0.0),
                "created_at": strategy.created_at.isoformat()
            })

        return summary

    async def _calculate_correlations(
        self,
        strategies: List[AutoPilotStrategy]
    ) -> List[StrategyCorrelation]:
        """
        Calculate correlation between strategy pairs using Greeks and position data.

        Correlation factors:
        - Same underlying (higher correlation)
        - Greeks direction similarity (delta sign, vega sign)
        - Strategy type compatibility
        - Expiry proximity
        """
        from app.models.autopilot import AutoPilotPositionLeg

        correlations = []

        # Get Greeks for all strategies
        strategy_greeks_map = {}
        for strategy in strategies:
            legs_result = await self.db.execute(
                select(AutoPilotPositionLeg).where(
                    AutoPilotPositionLeg.strategy_id == strategy.id
                )
            )
            legs = legs_result.scalars().all()

            total_delta = sum(leg.current_delta or 0 for leg in legs)
            total_vega = sum(leg.current_vega or 0 for leg in legs)
            total_theta = sum(leg.current_theta or 0 for leg in legs)

            strategy_greeks_map[strategy.id] = {
                'delta': total_delta,
                'vega': total_vega,
                'theta': total_theta,
                'legs_count': len(legs)
            }

        for i, strat1 in enumerate(strategies):
            for strat2 in strategies[i+1:]:
                corr = 0.0

                # Factor 1: Same underlying (0.3)
                if strat1.underlying == strat2.underlying:
                    corr += 0.3

                # Factor 2: Greeks direction similarity (0.4)
                greeks1 = strategy_greeks_map.get(strat1.id, {})
                greeks2 = strategy_greeks_map.get(strat2.id, {})

                if greeks1 and greeks2:
                    delta1, delta2 = greeks1.get('delta', 0), greeks2.get('delta', 0)
                    vega1, vega2 = greeks1.get('vega', 0), greeks2.get('vega', 0)

                    # Delta direction similarity
                    if delta1 != 0 and delta2 != 0:
                        if (delta1 > 0 and delta2 > 0) or (delta1 < 0 and delta2 < 0):
                            corr += 0.2  # Same directional bias
                        else:
                            corr -= 0.1  # Opposite directions = negative correlation

                    # Vega exposure similarity
                    if vega1 != 0 and vega2 != 0:
                        if (vega1 > 0 and vega2 > 0) or (vega1 < 0 and vega2 < 0):
                            corr += 0.2  # Similar volatility exposure
                        else:
                            corr -= 0.1

                # Factor 3: Both active (0.15)
                if strat1.status == "ACTIVE" and strat2.status == "ACTIVE":
                    corr += 0.15

                # Factor 4: Similar strategy types (0.15)
                if strat1.strategy_type == strat2.strategy_type:
                    corr += 0.15

                # Ensure correlation is between -1 and 1
                corr = max(-1.0, min(1.0, corr))

                # Diversification benefit (inverse of absolute correlation)
                diversification = 1.0 - abs(corr)

                correlations.append(StrategyCorrelation(
                    strategy1_id=strat1.id,
                    strategy2_id=strat2.id,
                    strategy1_name=strat1.name,
                    strategy2_name=strat2.name,
                    correlation=round(corr, 3),
                    diversification_benefit=round(diversification, 3)
                ))

        return correlations

    def _assess_portfolio_risk(
        self,
        greeks: PortfolioGreeks,
        capital_deployed: Decimal,
        total_capital: Decimal,
        correlations: List[StrategyCorrelation]
    ) -> Tuple[str, float]:
        """
        Assess overall portfolio risk level.

        Returns: (risk_level, risk_score)
        """

        risk_score = 0.0

        # Delta risk (0-25 points)
        delta_ratio = abs(float(greeks.delta_exposure)) / float(total_capital) if total_capital > 0 else 0
        delta_score = min(25.0, delta_ratio * 100)
        risk_score += delta_score

        # Gamma risk (0-25 points)
        gamma_score = min(25.0, abs(float(greeks.gamma_risk)) / 100)
        risk_score += gamma_score

        # Capital concentration (0-25 points)
        concentration = float(capital_deployed) / float(total_capital) if total_capital > 0 else 0
        concentration_score = min(25.0, concentration * 50)
        risk_score += concentration_score

        # Correlation risk (0-25 points)
        avg_correlation = sum(c.correlation for c in correlations) / len(correlations) if correlations else 0.0
        correlation_score = avg_correlation * 25
        risk_score += correlation_score

        # Determine risk level
        if risk_score < 30:
            risk_level = "LOW"
        elif risk_score < 50:
            risk_level = "MODERATE"
        elif risk_score < 75:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        return risk_level, risk_score

    async def _generate_rebalance_recommendations(
        self,
        strategies: List[AutoPilotStrategy],
        strategy_summary: List[Dict],
        greeks: PortfolioGreeks,
        total_capital: Decimal,
        correlations: List[StrategyCorrelation]
    ) -> List[PortfolioRebalance]:
        """Generate portfolio rebalancing recommendations"""

        recommendations = []

        # Check concentration limits
        for summary in strategy_summary:
            allocation = summary["capital_used"] / total_capital if total_capital > 0 else 0

            if allocation > self.MAX_CONCENTRATION:
                recommendations.append(PortfolioRebalance(
                    action="REDUCE",
                    strategy_id=summary["id"],
                    strategy_name=summary["name"],
                    current_allocation=summary["capital_used"],
                    recommended_allocation=total_capital * Decimal(str(self.MAX_CONCENTRATION)),
                    reason=f"Concentration {allocation:.1%} exceeds max {self.MAX_CONCENTRATION:.1%}",
                    priority=1
                ))

        # Check portfolio delta
        if abs(greeks.total_delta) > self.MAX_PORTFOLIO_DELTA:
            # Find strategy with highest delta contribution
            highest_delta_strat = max(
                greeks.strategy_greeks.items(),
                key=lambda x: abs(x[1]["delta"]),
                default=(None, None)
            )

            if highest_delta_strat[0]:
                strat_summary = next((s for s in strategy_summary if s["id"] == highest_delta_strat[0]), None)
                if strat_summary:
                    recommendations.append(PortfolioRebalance(
                        action="REDUCE",
                        strategy_id=strat_summary["id"],
                        strategy_name=strat_summary["name"],
                        current_allocation=strat_summary["capital_used"],
                        recommended_allocation=strat_summary["capital_used"] * Decimal("0.7"),
                        reason=f"Portfolio delta {greeks.total_delta} exceeds limit {self.MAX_PORTFOLIO_DELTA}",
                        priority=2
                    ))

        # Check high correlation pairs
        for corr in correlations:
            if corr.correlation > self.MAX_STRATEGY_CORRELATION:
                strat2_summary = next((s for s in strategy_summary if s["id"] == corr.strategy2_id), None)
                if strat2_summary:
                    recommendations.append(PortfolioRebalance(
                        action="REDUCE",
                        strategy_id=corr.strategy2_id,
                        strategy_name=corr.strategy2_name,
                        current_allocation=strat2_summary["capital_used"],
                        recommended_allocation=strat2_summary["capital_used"] * Decimal("0.5"),
                        reason=f"High correlation {corr.correlation:.2f} with {corr.strategy1_name}",
                        priority=3
                    ))

        # Sort by priority
        recommendations.sort(key=lambda x: x.priority)

        return recommendations

    def _empty_portfolio_summary(self, total_capital: Decimal) -> PortfolioSummary:
        """Return empty portfolio summary when no strategies exist"""

        return PortfolioSummary(
            total_strategies=0,
            active_strategies=0,
            total_capital_deployed=Decimal("0"),
            available_capital=total_capital,
            total_pnl=Decimal("0"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            portfolio_greeks=PortfolioGreeks(
                total_delta=Decimal("0"),
                total_gamma=Decimal("0"),
                total_theta=Decimal("0"),
                total_vega=Decimal("0"),
                delta_exposure=Decimal("0"),
                gamma_risk=Decimal("0"),
                theta_decay=Decimal("0"),
                vega_exposure=Decimal("0"),
                strategy_greeks={}
            ),
            risk_level="LOW",
            risk_score=0.0,
            strategy_summary=[],
            correlations=[],
            rebalance_recommendations=[]
        )


__all__ = [
    "PortfolioManager",
    "PortfolioSummary",
    "PortfolioGreeks",
    "StrategyCorrelation",
    "PortfolioRebalance"
]
