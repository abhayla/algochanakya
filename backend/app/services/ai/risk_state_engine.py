"""
Risk State Engine

Autonomous drawdown control state machine for AI trading.
Evaluates performance metrics and transitions between NORMAL, DEGRADED, and PAUSED states.
"""

import logging
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from uuid import UUID

from app.models.ai_risk_state import AIRiskState, RiskState
from app.models.ai import AIUserConfig, AILearningReport

logger = logging.getLogger(__name__)


class RiskStateEngine:
    """
    Autonomous drawdown control engine.

    State Machine:
    NORMAL -> DEGRADED -> PAUSED

    Auto-Transition Rules:
    - NORMAL -> DEGRADED:
        - Sharpe < 0.5 over 20 trades OR
        - Drawdown > 10%
    - DEGRADED -> PAUSED:
        - Drawdown > 20% OR
        - Sharpe < 0 over 20 trades
    - PAUSED/DEGRADED -> NORMAL:
        - Manual recovery OR
        - Performance improvement (Sharpe > 0.7 and Drawdown < 5%)

    DEGRADED Behavior:
    - Increase min_confidence_to_trade by 15%
    - Reduce lot multiplier by 50%
    - Disable offensive adjustments
    """

    # State transition thresholds
    SHARPE_DEGRADED_THRESHOLD = 0.5
    SHARPE_PAUSED_THRESHOLD = 0.0
    SHARPE_RECOVERY_THRESHOLD = 0.7

    DRAWDOWN_DEGRADED_THRESHOLD = Decimal('10.00')  # 10%
    DRAWDOWN_PAUSED_THRESHOLD = Decimal('20.00')    # 20%
    DRAWDOWN_RECOVERY_THRESHOLD = Decimal('5.00')   # 5%

    MIN_TRADES_FOR_EVALUATION = 20
    CONSECUTIVE_LOSSES_ALERT = 3

    # DEGRADED mode adjustments
    DEGRADED_CONFIDENCE_INCREASE = Decimal('15.00')  # +15%
    DEGRADED_LOT_MULTIPLIER = 0.5                    # 50% reduction

    def __init__(self, db: AsyncSession):
        """
        Initialize Risk State Engine.

        Args:
            db: Async database session
        """
        self.db = db

    async def evaluate_state(self, user_id: UUID) -> Tuple[RiskState, Optional[str]]:
        """
        Evaluate current risk state based on performance metrics.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (recommended_state, reason)
        """
        try:
            # Get current risk state
            current_state_record = await self._get_or_create_risk_state(user_id)
            current_state = RiskState(current_state_record.state)

            # Get performance metrics
            sharpe_ratio, drawdown, consecutive_losses = await self._get_performance_metrics(user_id)

            logger.debug(
                f"User {user_id} metrics: Sharpe={sharpe_ratio}, DD={drawdown}%, "
                f"Consecutive Losses={consecutive_losses}, Current State={current_state}"
            )

            # Evaluate state transitions
            recommended_state, reason = self._evaluate_transition(
                current_state=current_state,
                sharpe_ratio=sharpe_ratio,
                drawdown=drawdown,
                consecutive_losses=consecutive_losses
            )

            return recommended_state, reason

        except Exception as e:
            logger.error(f"Error evaluating risk state for user {user_id}: {e}")
            return RiskState.NORMAL, None

    async def transition_state(
        self,
        user_id: UUID,
        new_state: RiskState,
        reason: str,
        sharpe_ratio: Optional[float] = None,
        drawdown: Optional[Decimal] = None,
        consecutive_losses: int = 0
    ) -> AIRiskState:
        """
        Transition user to a new risk state with audit trail.

        Args:
            user_id: User UUID
            new_state: New risk state
            reason: Reason for transition
            sharpe_ratio: Current Sharpe ratio
            drawdown: Current drawdown percentage
            consecutive_losses: Current consecutive losses

        Returns:
            Updated AIRiskState record
        """
        try:
            # Get or create risk state record
            risk_state_record = await self._get_or_create_risk_state(user_id)

            # Store previous state
            previous_state = risk_state_record.state

            # Update state
            risk_state_record.previous_state = previous_state
            risk_state_record.state = new_state.value
            risk_state_record.reason = reason
            risk_state_record.sharpe_ratio = Decimal(str(sharpe_ratio)) if sharpe_ratio is not None else None
            risk_state_record.current_drawdown = drawdown
            risk_state_record.consecutive_losses = consecutive_losses
            risk_state_record.triggered_at = datetime.utcnow()

            # Clear resolved_at if transitioning to DEGRADED or PAUSED
            if new_state in [RiskState.DEGRADED, RiskState.PAUSED]:
                risk_state_record.resolved_at = None
            elif new_state == RiskState.NORMAL and previous_state != 'NORMAL':
                risk_state_record.resolved_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(risk_state_record)

            logger.info(
                f"User {user_id} risk state transition: {previous_state} -> {new_state.value}. "
                f"Reason: {reason}"
            )

            return risk_state_record

        except Exception as e:
            logger.error(f"Error transitioning risk state for user {user_id}: {e}")
            await self.db.rollback()
            raise

    async def get_current_state(self, user_id: UUID) -> AIRiskState:
        """
        Get current risk state for user.

        Args:
            user_id: User UUID

        Returns:
            AIRiskState record
        """
        return await self._get_or_create_risk_state(user_id)

    async def apply_degraded_adjustments(
        self,
        user_config: AIUserConfig
    ) -> Dict[str, any]:
        """
        Apply DEGRADED mode adjustments to user configuration.

        Args:
            user_config: User's AI configuration

        Returns:
            Dict with adjusted parameters
        """
        if not user_config:
            return {}

        # Increase confidence threshold by 15%
        adjusted_confidence = min(
            user_config.min_confidence_to_trade + self.DEGRADED_CONFIDENCE_INCREASE,
            Decimal('95.00')  # Cap at 95%
        )

        # Reduce lot multipliers by 50%
        adjusted_tiers = []
        for tier in user_config.confidence_tiers:
            adjusted_tier = tier.copy()
            adjusted_tier['multiplier'] = tier['multiplier'] * self.DEGRADED_LOT_MULTIPLIER
            adjusted_tiers.append(adjusted_tier)

        return {
            'min_confidence_to_trade': adjusted_confidence,
            'confidence_tiers': adjusted_tiers,
            'max_lots_per_strategy': max(1, int(user_config.max_lots_per_strategy * self.DEGRADED_LOT_MULTIPLIER)),
            'max_strategies_per_day': max(1, int(user_config.max_strategies_per_day * self.DEGRADED_LOT_MULTIPLIER)),
            'adjustments_disabled': True  # Disable offensive adjustments
        }

    def _evaluate_transition(
        self,
        current_state: RiskState,
        sharpe_ratio: Optional[float],
        drawdown: Optional[Decimal],
        consecutive_losses: int
    ) -> Tuple[RiskState, Optional[str]]:
        """
        Evaluate if state transition is needed.

        Args:
            current_state: Current risk state
            sharpe_ratio: Sharpe ratio over recent trades
            drawdown: Current drawdown percentage
            consecutive_losses: Number of consecutive losses

        Returns:
            Tuple of (recommended_state, reason)
        """
        reasons = []

        # Check PAUSED conditions (highest priority)
        if drawdown and drawdown >= self.DRAWDOWN_PAUSED_THRESHOLD:
            reasons.append(f"Drawdown {drawdown}% >= {self.DRAWDOWN_PAUSED_THRESHOLD}%")
            return RiskState.PAUSED, "; ".join(reasons)

        if sharpe_ratio is not None and sharpe_ratio < self.SHARPE_PAUSED_THRESHOLD:
            reasons.append(f"Sharpe ratio {sharpe_ratio:.3f} < {self.SHARPE_PAUSED_THRESHOLD}")
            return RiskState.PAUSED, "; ".join(reasons)

        # Check DEGRADED conditions
        degraded_triggers = []

        if drawdown and drawdown >= self.DRAWDOWN_DEGRADED_THRESHOLD:
            degraded_triggers.append(f"Drawdown {drawdown}% >= {self.DRAWDOWN_DEGRADED_THRESHOLD}%")

        if sharpe_ratio is not None and sharpe_ratio < self.SHARPE_DEGRADED_THRESHOLD:
            degraded_triggers.append(f"Sharpe ratio {sharpe_ratio:.3f} < {self.SHARPE_DEGRADED_THRESHOLD}")

        if consecutive_losses >= self.CONSECUTIVE_LOSSES_ALERT:
            degraded_triggers.append(f"Consecutive losses: {consecutive_losses}")

        if degraded_triggers:
            return RiskState.DEGRADED, "; ".join(degraded_triggers)

        # Check RECOVERY conditions (from DEGRADED/PAUSED back to NORMAL)
        if current_state in [RiskState.DEGRADED, RiskState.PAUSED]:
            recovery_met = True
            recovery_reasons = []

            if sharpe_ratio is None or sharpe_ratio < self.SHARPE_RECOVERY_THRESHOLD:
                recovery_met = False
            else:
                recovery_reasons.append(f"Sharpe ratio recovered to {sharpe_ratio:.3f}")

            if drawdown is None or drawdown >= self.DRAWDOWN_RECOVERY_THRESHOLD:
                recovery_met = False
            else:
                recovery_reasons.append(f"Drawdown reduced to {drawdown}%")

            if recovery_met and recovery_reasons:
                return RiskState.NORMAL, f"Recovery: {'; '.join(recovery_reasons)}"

        # No state change needed
        return current_state, None

    async def _get_or_create_risk_state(self, user_id: UUID) -> AIRiskState:
        """
        Get or create risk state record for user.

        Args:
            user_id: User UUID

        Returns:
            AIRiskState record
        """
        # Try to get existing record
        stmt = select(AIRiskState).where(AIRiskState.user_id == user_id)
        result = await self.db.execute(stmt)
        risk_state = result.scalar_one_or_none()

        if risk_state:
            return risk_state

        # Create new record with NORMAL state
        risk_state = AIRiskState(
            user_id=user_id,
            state=RiskState.NORMAL.value,
            consecutive_losses=0
        )
        self.db.add(risk_state)
        await self.db.commit()
        await self.db.refresh(risk_state)

        logger.info(f"Created new risk state record for user {user_id} with state=NORMAL")
        return risk_state

    async def _get_performance_metrics(
        self,
        user_id: UUID
    ) -> Tuple[Optional[float], Optional[Decimal], int]:
        """
        Calculate performance metrics from recent trading history.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (sharpe_ratio, drawdown_pct, consecutive_losses)
        """
        try:
            # Get recent learning reports (last 20 trading days or more)
            stmt = (
                select(AILearningReport)
                .where(AILearningReport.user_id == user_id)
                .where(AILearningReport.total_trades > 0)
                .order_by(desc(AILearningReport.report_date))
                .limit(30)  # Get more to ensure we have enough data
            )
            result = await self.db.execute(stmt)
            reports = result.scalars().all()

            if not reports:
                logger.debug(f"No learning reports found for user {user_id}")
                return None, None, 0

            # Calculate total trades across reports
            total_trades = sum(r.total_trades for r in reports)

            if total_trades < self.MIN_TRADES_FOR_EVALUATION:
                logger.debug(
                    f"Insufficient trades for evaluation: {total_trades} < {self.MIN_TRADES_FOR_EVALUATION}"
                )
                return None, None, 0

            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio(reports)

            # Calculate drawdown
            drawdown = self._calculate_drawdown(reports)

            # Calculate consecutive losses (from most recent reports)
            consecutive_losses = self._calculate_consecutive_losses(reports)

            return sharpe_ratio, drawdown, consecutive_losses

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return None, None, 0

    def _calculate_sharpe_ratio(self, reports: List[AILearningReport]) -> Optional[float]:
        """
        Calculate Sharpe ratio from learning reports.

        Sharpe Ratio = Mean(Returns) / StdDev(Returns)

        Args:
            reports: List of AILearningReport records

        Returns:
            Sharpe ratio or None
        """
        try:
            # Extract daily returns
            returns = [float(r.total_pnl) for r in reports if r.total_pnl]

            if len(returns) < 2:
                return None

            # Calculate mean and standard deviation
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5

            if std_dev == 0:
                return None

            sharpe_ratio = mean_return / std_dev

            return sharpe_ratio

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return None

    def _calculate_drawdown(self, reports: List[AILearningReport]) -> Optional[Decimal]:
        """
        Calculate current drawdown percentage.

        Drawdown = (Peak - Current) / Peak * 100

        Args:
            reports: List of AILearningReport records (ordered by date desc)

        Returns:
            Drawdown percentage or None
        """
        try:
            if not reports:
                return None

            # Calculate cumulative P&L series (reverse to chronological order)
            cumulative_pnl = []
            running_total = Decimal('0')

            for report in reversed(reports):
                running_total += report.total_pnl
                cumulative_pnl.append(running_total)

            if not cumulative_pnl:
                return Decimal('0')

            # Find peak and current value
            peak = max(cumulative_pnl)
            current = cumulative_pnl[-1]

            # If current is at peak or peak is 0, no drawdown
            if current >= peak or peak <= 0:
                return Decimal('0')

            # Calculate drawdown percentage
            drawdown_pct = ((peak - current) / peak) * 100

            return Decimal(str(drawdown_pct)).quantize(Decimal('0.01'))

        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return None

    def _calculate_consecutive_losses(self, reports: List[AILearningReport]) -> int:
        """
        Calculate current consecutive losing trades.

        Args:
            reports: List of AILearningReport records (ordered by date desc)

        Returns:
            Number of consecutive losses
        """
        try:
            consecutive_losses = 0

            # Count consecutive losses from most recent
            for report in reports:
                if report.losing_trades > 0 and report.winning_trades == 0:
                    consecutive_losses += report.losing_trades
                else:
                    break

            return consecutive_losses

        except Exception as e:
            logger.error(f"Error calculating consecutive losses: {e}")
            return 0


__all__ = ["RiskStateEngine", "RiskState"]
