"""
Capital-at-Risk Meter Service - Priority 3.3

Calculates real-time capital-at-risk metrics for AI trading.
Accounts for worst-case daily risk under stress scenarios.

Key Features:
- Calculate worst-case daily risk
- Account for stress scenarios (VaR-like analysis)
- Track capital utilization
- Alert when thresholds breached
- Integration with user limits and positions

Usage:
    meter = CapitalRiskMeter(db, stress_engine)
    risk_metrics = await meter.calculate_capital_at_risk(user_id)
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.ai import AIUserConfig
from app.models.ai_risk_state import AIRiskState, RiskState
from app.services.ai.stress_greeks_engine import StressGreeksEngine, StressTestResult

logger = logging.getLogger(__name__)

# Default stress scenarios for daily VaR calculation
DAILY_VAR_SCENARIOS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]

# Alert severity thresholds
ALERT_THRESHOLDS = {
    'CRITICAL': 90,  # >= 90% of capital at risk
    'HIGH': 75,      # >= 75%
    'ELEVATED': 60,  # >= 60%
    'NORMAL': 40,    # >= 40%
}


@dataclass
class CapitalRiskAlert:
    """Represents a capital risk alert."""
    severity: str  # CRITICAL, HIGH, ELEVATED, NORMAL, LOW
    message: str
    metric: str
    current_value: float
    threshold: float
    triggered_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity,
            'message': self.message,
            'metric': self.metric,
            'current_value': round(self.current_value, 2),
            'threshold': round(self.threshold, 2),
            'triggered_at': self.triggered_at.isoformat()
        }


@dataclass
class CapitalRiskMetrics:
    """Capital-at-risk metrics."""
    user_id: str

    # Core capital metrics
    max_daily_capital: float       # User's daily capital limit
    deployed_capital: float        # Currently deployed (margin used)
    capital_utilization_pct: float # deployed / max * 100

    # Risk metrics
    worst_case_loss: float         # Worst-case loss from stress scenarios
    capital_at_risk: float         # Total capital at risk
    capital_at_risk_pct: float     # capital_at_risk / max_daily_capital * 100

    # Stress metrics
    var_95: float                  # Value at Risk (95% confidence)
    expected_shortfall: float      # Expected loss in worst 5% of scenarios
    stress_risk_score: float       # From stress engine (0-100)

    # Position metrics
    open_positions_count: int
    total_exposure: float          # Sum of notional values

    # Alert status
    alert_level: str               # CRITICAL, HIGH, ELEVATED, NORMAL, LOW
    alerts: List[CapitalRiskAlert]

    # Thresholds (user configured)
    warning_threshold_pct: float
    critical_threshold_pct: float

    # Metadata
    calculated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'max_daily_capital': round(self.max_daily_capital, 2),
            'deployed_capital': round(self.deployed_capital, 2),
            'capital_utilization_pct': round(self.capital_utilization_pct, 2),
            'worst_case_loss': round(self.worst_case_loss, 2),
            'capital_at_risk': round(self.capital_at_risk, 2),
            'capital_at_risk_pct': round(self.capital_at_risk_pct, 2),
            'var_95': round(self.var_95, 2),
            'expected_shortfall': round(self.expected_shortfall, 2),
            'stress_risk_score': round(self.stress_risk_score, 2),
            'open_positions_count': self.open_positions_count,
            'total_exposure': round(self.total_exposure, 2),
            'alert_level': self.alert_level,
            'alerts': [a.to_dict() for a in self.alerts],
            'warning_threshold_pct': self.warning_threshold_pct,
            'critical_threshold_pct': self.critical_threshold_pct,
            'calculated_at': self.calculated_at.isoformat()
        }


class CapitalRiskMeter:
    """
    Capital-at-Risk Meter for AI trading.

    Calculates and monitors capital risk metrics in real-time.
    Provides alerts when thresholds are breached.
    """

    DEFAULT_MAX_DAILY_CAPITAL = 500000  # ₹5 lakhs default
    DEFAULT_WARNING_THRESHOLD = 70      # 70%
    DEFAULT_CRITICAL_THRESHOLD = 90     # 90%

    def __init__(
        self,
        db: AsyncSession,
        stress_engine: Optional[StressGreeksEngine] = None
    ):
        """
        Initialize Capital Risk Meter.

        Args:
            db: Async database session
            stress_engine: Optional StressGreeksEngine for stress calculations
        """
        self.db = db
        self.stress_engine = stress_engine

    async def calculate_capital_at_risk(
        self,
        user_id: UUID,
        positions: Optional[List[Dict[str, Any]]] = None,
        current_spot: Optional[float] = None
    ) -> CapitalRiskMetrics:
        """
        Calculate capital-at-risk metrics for a user.

        Args:
            user_id: User UUID
            positions: Optional list of current positions (legs format)
            current_spot: Optional current spot price

        Returns:
            CapitalRiskMetrics with all risk metrics
        """
        try:
            # Get user configuration
            user_config = await self._get_user_config(user_id)

            # Calculate deployed capital and exposure
            deployed_capital, total_exposure, positions_count = await self._calculate_deployed_capital(
                user_id, positions
            )

            # Get max daily capital from user config
            max_daily_capital = float(
                user_config.daily_loss_limit if user_config
                else self.DEFAULT_MAX_DAILY_CAPITAL
            )

            # Calculate capital utilization
            capital_utilization_pct = (
                (deployed_capital / max_daily_capital * 100)
                if max_daily_capital > 0 else 0
            )

            # Calculate worst-case loss from stress scenarios
            worst_case_loss, var_95, expected_shortfall, stress_risk_score = (
                await self._calculate_stress_metrics(
                    positions or [],
                    current_spot or 22000.0  # Default spot if not provided
                )
            )

            # Calculate total capital at risk
            capital_at_risk = deployed_capital + abs(worst_case_loss)
            capital_at_risk_pct = (
                (capital_at_risk / max_daily_capital * 100)
                if max_daily_capital > 0 else 0
            )

            # Get user thresholds
            warning_threshold = float(
                user_config.stress_max_var_pct if user_config and user_config.stress_max_var_pct
                else self.DEFAULT_WARNING_THRESHOLD
            )
            critical_threshold = float(
                user_config.stress_max_delta if user_config and user_config.stress_max_delta
                else self.DEFAULT_CRITICAL_THRESHOLD
            )

            # Determine alert level and generate alerts
            alert_level, alerts = self._evaluate_alerts(
                capital_at_risk_pct=capital_at_risk_pct,
                capital_utilization_pct=capital_utilization_pct,
                stress_risk_score=stress_risk_score,
                worst_case_loss=worst_case_loss,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                max_daily_capital=max_daily_capital
            )

            return CapitalRiskMetrics(
                user_id=str(user_id),
                max_daily_capital=max_daily_capital,
                deployed_capital=deployed_capital,
                capital_utilization_pct=capital_utilization_pct,
                worst_case_loss=worst_case_loss,
                capital_at_risk=capital_at_risk,
                capital_at_risk_pct=capital_at_risk_pct,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                stress_risk_score=stress_risk_score,
                open_positions_count=positions_count,
                total_exposure=total_exposure,
                alert_level=alert_level,
                alerts=alerts,
                warning_threshold_pct=warning_threshold,
                critical_threshold_pct=critical_threshold,
                calculated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error calculating capital-at-risk for user {user_id}: {e}")
            # Return safe defaults on error
            return self._get_default_metrics(user_id)

    async def check_deployment_risk(
        self,
        user_id: UUID,
        new_position: Dict[str, Any],
        current_spot: float
    ) -> Dict[str, Any]:
        """
        Check if deploying a new position would breach risk limits.

        Args:
            user_id: User UUID
            new_position: Position details (legs, margin_required, etc.)
            current_spot: Current spot price

        Returns:
            Dict with can_deploy and reasons
        """
        try:
            # Get current risk metrics
            current_metrics = await self.calculate_capital_at_risk(user_id)

            # Simulate new position impact
            new_margin = new_position.get('margin_required', 0)
            projected_deployed = current_metrics.deployed_capital + new_margin

            # Calculate projected capital utilization
            projected_utilization = (
                (projected_deployed / current_metrics.max_daily_capital * 100)
                if current_metrics.max_daily_capital > 0 else 0
            )

            # Check limits
            violations = []

            if projected_utilization > current_metrics.critical_threshold_pct:
                violations.append(
                    f"Projected capital utilization ({projected_utilization:.1f}%) "
                    f"exceeds critical threshold ({current_metrics.critical_threshold_pct}%)"
                )

            if current_metrics.alert_level == 'CRITICAL':
                violations.append(
                    f"Current risk level is CRITICAL - new deployments blocked"
                )

            # If stress engine available, check stress impact
            if self.stress_engine and new_position.get('legs'):
                stress_result = await self.stress_engine.calculate_stress_scenarios(
                    legs=new_position['legs'],
                    current_spot=current_spot,
                    lot_size=new_position.get('lot_size', 1)
                )

                if stress_result.stress_risk_score > 75:
                    violations.append(
                        f"New position stress risk score ({stress_result.stress_risk_score:.1f}) "
                        f"exceeds limit (75)"
                    )

            can_deploy = len(violations) == 0

            return {
                'can_deploy': can_deploy,
                'current_capital_at_risk_pct': round(current_metrics.capital_at_risk_pct, 2),
                'projected_capital_utilization_pct': round(projected_utilization, 2),
                'current_alert_level': current_metrics.alert_level,
                'violations': violations,
                'recommendation': (
                    'Safe to deploy' if can_deploy
                    else 'Reduce existing exposure before deploying new positions'
                )
            }

        except Exception as e:
            logger.error(f"Error checking deployment risk: {e}")
            return {
                'can_deploy': False,
                'violations': [f"Error checking risk: {str(e)}"],
                'recommendation': 'Unable to verify risk - deployment blocked'
            }

    async def get_risk_thresholds(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get user's risk thresholds configuration.

        Args:
            user_id: User UUID

        Returns:
            Dict with threshold configuration
        """
        user_config = await self._get_user_config(user_id)

        return {
            'max_daily_capital': float(
                user_config.daily_loss_limit if user_config
                else self.DEFAULT_MAX_DAILY_CAPITAL
            ),
            'warning_threshold_pct': float(
                user_config.stress_max_var_pct if user_config and user_config.stress_max_var_pct
                else self.DEFAULT_WARNING_THRESHOLD
            ),
            'critical_threshold_pct': float(
                user_config.stress_max_delta if user_config and user_config.stress_max_delta
                else self.DEFAULT_CRITICAL_THRESHOLD
            ),
            'max_strategies_per_day': (
                user_config.max_strategies_per_day if user_config else 3
            ),
            'max_lots_per_strategy': (
                user_config.max_lots_per_strategy if user_config else 2
            ),
            'description': {
                'warning': 'Elevated risk - reduce position size or exit some positions',
                'critical': 'High risk - new deployments blocked, consider reducing exposure'
            }
        }

    async def _get_user_config(self, user_id: UUID) -> Optional[AIUserConfig]:
        """Get user's AI configuration."""
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _calculate_deployed_capital(
        self,
        user_id: UUID,
        positions: Optional[List[Dict[str, Any]]]
    ) -> tuple:
        """
        Calculate deployed capital from positions.

        Returns:
            Tuple of (deployed_capital, total_exposure, positions_count)
        """
        if not positions:
            return 0.0, 0.0, 0

        deployed_capital = 0.0
        total_exposure = 0.0

        for position in positions:
            # Sum up margin requirements
            deployed_capital += position.get('margin_required', 0)
            deployed_capital += position.get('premium_paid', 0)

            # Sum up notional exposure
            strike = position.get('strike', 0)
            qty = abs(position.get('quantity', 0))
            total_exposure += strike * qty

        return deployed_capital, total_exposure, len(positions)

    async def _calculate_stress_metrics(
        self,
        positions: List[Dict[str, Any]],
        current_spot: float
    ) -> tuple:
        """
        Calculate stress-based risk metrics.

        Returns:
            Tuple of (worst_case_loss, var_95, expected_shortfall, stress_risk_score)
        """
        if not self.stress_engine or not positions:
            return 0.0, 0.0, 0.0, 0.0

        try:
            # Convert positions to legs format
            legs = []
            for pos in positions:
                leg = {
                    'instrument_type': pos.get('instrument_type', 'OPT'),
                    'option_type': pos.get('option_type', 'CE'),
                    'strike': pos.get('strike', 22000),
                    'expiry': pos.get('expiry'),
                    'quantity': pos.get('quantity', 1),
                    'premium': pos.get('premium', 0),
                    'iv': pos.get('iv', 0.2)
                }
                legs.append(leg)

            # Run stress test
            stress_result = await self.stress_engine.calculate_stress_scenarios(
                legs=legs,
                current_spot=current_spot,
                lot_size=1
            )

            # Extract metrics
            worst_case_loss = abs(stress_result.risk_metrics.get('max_loss', 0))

            # Calculate VaR (95th percentile loss)
            pnl_values = [s.estimated_pnl for s in stress_result.scenarios]
            pnl_values_sorted = sorted(pnl_values)
            var_95_index = int(len(pnl_values_sorted) * 0.05)
            var_95 = abs(pnl_values_sorted[var_95_index]) if pnl_values_sorted else 0

            # Expected shortfall (average of worst 5%)
            worst_pnls = pnl_values_sorted[:max(1, var_95_index)]
            expected_shortfall = abs(sum(worst_pnls) / len(worst_pnls)) if worst_pnls else 0

            return (
                worst_case_loss,
                var_95,
                expected_shortfall,
                stress_result.stress_risk_score
            )

        except Exception as e:
            logger.error(f"Error calculating stress metrics: {e}")
            return 0.0, 0.0, 0.0, 0.0

    def _evaluate_alerts(
        self,
        capital_at_risk_pct: float,
        capital_utilization_pct: float,
        stress_risk_score: float,
        worst_case_loss: float,
        warning_threshold: float,
        critical_threshold: float,
        max_daily_capital: float
    ) -> tuple:
        """
        Evaluate risk alerts.

        Returns:
            Tuple of (alert_level, list of alerts)
        """
        alerts = []
        current_time = datetime.utcnow()

        # Capital-at-risk alerts
        if capital_at_risk_pct >= critical_threshold:
            alerts.append(CapitalRiskAlert(
                severity='CRITICAL',
                message=f'Capital at risk ({capital_at_risk_pct:.1f}%) exceeds critical threshold',
                metric='capital_at_risk_pct',
                current_value=capital_at_risk_pct,
                threshold=critical_threshold,
                triggered_at=current_time
            ))
        elif capital_at_risk_pct >= warning_threshold:
            alerts.append(CapitalRiskAlert(
                severity='HIGH',
                message=f'Capital at risk ({capital_at_risk_pct:.1f}%) exceeds warning threshold',
                metric='capital_at_risk_pct',
                current_value=capital_at_risk_pct,
                threshold=warning_threshold,
                triggered_at=current_time
            ))

        # Utilization alerts
        if capital_utilization_pct >= 90:
            alerts.append(CapitalRiskAlert(
                severity='HIGH',
                message=f'Capital utilization ({capital_utilization_pct:.1f}%) is very high',
                metric='capital_utilization_pct',
                current_value=capital_utilization_pct,
                threshold=90,
                triggered_at=current_time
            ))
        elif capital_utilization_pct >= 75:
            alerts.append(CapitalRiskAlert(
                severity='ELEVATED',
                message=f'Capital utilization ({capital_utilization_pct:.1f}%) is elevated',
                metric='capital_utilization_pct',
                current_value=capital_utilization_pct,
                threshold=75,
                triggered_at=current_time
            ))

        # Stress risk alerts
        if stress_risk_score >= 75:
            alerts.append(CapitalRiskAlert(
                severity='HIGH',
                message=f'Stress risk score ({stress_risk_score:.1f}) indicates high tail risk',
                metric='stress_risk_score',
                current_value=stress_risk_score,
                threshold=75,
                triggered_at=current_time
            ))
        elif stress_risk_score >= 50:
            alerts.append(CapitalRiskAlert(
                severity='ELEVATED',
                message=f'Stress risk score ({stress_risk_score:.1f}) indicates moderate tail risk',
                metric='stress_risk_score',
                current_value=stress_risk_score,
                threshold=50,
                triggered_at=current_time
            ))

        # Worst-case loss alerts (as % of capital)
        loss_pct = (worst_case_loss / max_daily_capital * 100) if max_daily_capital > 0 else 0
        if loss_pct >= 20:
            alerts.append(CapitalRiskAlert(
                severity='HIGH',
                message=f'Worst-case loss (₹{worst_case_loss:,.0f}) is {loss_pct:.1f}% of daily capital',
                metric='worst_case_loss_pct',
                current_value=loss_pct,
                threshold=20,
                triggered_at=current_time
            ))

        # Determine overall alert level
        if any(a.severity == 'CRITICAL' for a in alerts):
            alert_level = 'CRITICAL'
        elif any(a.severity == 'HIGH' for a in alerts):
            alert_level = 'HIGH'
        elif any(a.severity == 'ELEVATED' for a in alerts):
            alert_level = 'ELEVATED'
        elif capital_at_risk_pct >= 40:
            alert_level = 'NORMAL'
        else:
            alert_level = 'LOW'

        return alert_level, alerts

    def _get_default_metrics(self, user_id: UUID) -> CapitalRiskMetrics:
        """Return default metrics on error."""
        return CapitalRiskMetrics(
            user_id=str(user_id),
            max_daily_capital=self.DEFAULT_MAX_DAILY_CAPITAL,
            deployed_capital=0,
            capital_utilization_pct=0,
            worst_case_loss=0,
            capital_at_risk=0,
            capital_at_risk_pct=0,
            var_95=0,
            expected_shortfall=0,
            stress_risk_score=0,
            open_positions_count=0,
            total_exposure=0,
            alert_level='LOW',
            alerts=[],
            warning_threshold_pct=self.DEFAULT_WARNING_THRESHOLD,
            critical_threshold_pct=self.DEFAULT_CRITICAL_THRESHOLD,
            calculated_at=datetime.utcnow()
        )


__all__ = ["CapitalRiskMeter", "CapitalRiskMetrics", "CapitalRiskAlert"]
