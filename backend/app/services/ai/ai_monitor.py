"""
AI Monitor Service

Monitors AI-managed AutoPilot strategies and makes intelligent decisions:
- Detects regime changes and suggests adjustments
- Evaluates position health
- Recommends entry/exit actions
- Logs all AI decisions with reasoning

Integrates with the existing strategy_monitor.py for AutoPilot.
"""

import logging
from typing import List, Dict, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.ai import AIUserConfig
from app.services.ai.market_regime import MarketRegimeClassifier, RegimeType
from app.services.ai.strategy_recommender import StrategyRecommender
from app.services.ai.position_sync import PositionSyncService, PositionAnalysis
from app.services.ai.claude_advisor import ClaudeAdvisor

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse

logger = logging.getLogger(__name__)


class AIDecision:
    """Represents a single AI decision."""

    def __init__(
        self,
        decision_type: str,  # strategy_selection, entry, adjustment, exit
        action_taken: str,
        confidence: float,
        reasoning: str,
        regime_at_decision: str,
        vix_at_decision: float,
        spot_at_decision: float,
        indicators_snapshot: Dict
    ):
        self.decision_type = decision_type
        self.action_taken = action_taken
        self.confidence = confidence
        self.reasoning = reasoning
        self.regime_at_decision = regime_at_decision
        self.vix_at_decision = vix_at_decision
        self.spot_at_decision = spot_at_decision
        self.indicators_snapshot = indicators_snapshot
        self.decision_time = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "decision_type": self.decision_type,
            "action_taken": self.action_taken,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "regime_at_decision": self.regime_at_decision,
            "vix_at_decision": self.vix_at_decision,
            "spot_at_decision": self.spot_at_decision,
            "indicators_snapshot": self.indicators_snapshot,
            "decision_time": self.decision_time.isoformat()
        }


class AIMonitor:
    """
    Monitors AI-managed strategies and makes intelligent decisions.

    Called every 5 seconds by strategy_monitor.py during market hours.
    """

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.recommender = StrategyRecommender(db)
        self.position_sync = PositionSyncService(kite, db)
        self.claude_advisor = ClaudeAdvisor()
        self._last_regime: Optional[RegimeResponse] = None
        self._regime_change_threshold = 15.0  # % confidence change

    async def process_ai_strategies(
        self,
        user_id: str,
        user_config: AIUserConfig,
        active_strategies: List[Dict]
    ) -> List[AIDecision]:
        """
        Main AI monitoring loop called every 5 seconds.

        Args:
            user_id: User ID
            user_config: User's AI configuration
            active_strategies: List of active AutoPilot strategies

        Returns:
            List of AI decisions made during this cycle
        """
        decisions = []

        try:
            # Skip if AI is not enabled
            if not user_config.ai_enabled:
                return decisions

            logger.debug(f"Processing AI strategies for user {user_id}")

            # Step 1: Sync positions from broker
            position_analysis = await self.position_sync.sync_positions(user_id)

            # Step 2: Check for regime changes
            regime_decision = await self._check_regime_change(user_config)
            if regime_decision:
                decisions.append(regime_decision)

            # Step 3: Evaluate position health
            health_decision = await self._evaluate_position_health(
                position_analysis,
                user_config
            )
            if health_decision:
                decisions.append(health_decision)

            # Step 4: Check for adjustment opportunities
            for strategy in active_strategies:
                adjustment_decision = await self._evaluate_adjustment(
                    strategy,
                    user_config
                )
                if adjustment_decision:
                    decisions.append(adjustment_decision)

            # Step 5: Log all decisions to database
            for decision in decisions:
                await self._log_decision(user_id, decision)

            logger.debug(f"AI cycle complete: {len(decisions)} decisions made")
            return decisions

        except Exception as e:
            logger.error(f"Error in AI monitoring: {e}")
            return decisions

    async def _check_regime_change(
        self,
        user_config: AIUserConfig
    ) -> Optional[AIDecision]:
        """
        Check if market regime has changed significantly.

        Args:
            user_config: User configuration

        Returns:
            AIDecision if regime changed significantly, None otherwise
        """
        try:
            # Use MarketRegimeClassifier to get current regime
            classifier = MarketRegimeClassifier()

            # Get regime for user's preferred underlying (default to NIFTY)
            preferred_underlyings = user_config.preferred_underlyings or ["NIFTY"]
            underlying = preferred_underlyings[0] if preferred_underlyings else "NIFTY"

            current_regime = await classifier.classify(underlying)

            if not current_regime:
                logger.debug("Unable to classify current regime")
                return None

            # Initialize last regime if not set
            if not self._last_regime:
                self._last_regime = current_regime
                return None

            # Check if regime type changed
            regime_changed = (
                current_regime.regime_type != self._last_regime.regime_type
            )

            # Or confidence changed significantly
            confidence_delta = abs(
                current_regime.confidence - self._last_regime.confidence
            )
            confidence_changed = confidence_delta > self._regime_change_threshold

            if regime_changed or confidence_changed:
                logger.info(
                    f"Regime change detected: {self._last_regime.regime_type} "
                    f"({self._last_regime.confidence:.1f}%) -> {current_regime.regime_type} "
                    f"({current_regime.confidence:.1f}%)"
                )

                decision = AIDecision(
                    decision_type="regime_change",
                    action_taken=f"Regime changed to {current_regime.regime_type}",
                    confidence=current_regime.confidence,
                    reasoning=current_regime.reasoning,
                    regime_at_decision=str(current_regime.regime_type),
                    vix_at_decision=current_regime.indicators.vix or 0.0,
                    spot_at_decision=current_regime.indicators.spot_price,
                    indicators_snapshot={
                        "rsi_14": current_regime.indicators.rsi_14,
                        "adx_14": current_regime.indicators.adx_14,
                        "ema_50": current_regime.indicators.ema_50,
                        "underlying": underlying
                    }
                )

                self._last_regime = current_regime
                return decision

            return None

        except Exception as e:
            logger.error(f"Error checking regime change: {e}")
            return None

    async def _evaluate_position_health(
        self,
        analysis: PositionAnalysis,
        user_config: AIUserConfig
    ) -> Optional[AIDecision]:
        """
        Evaluate portfolio health and suggest actions.

        Args:
            analysis: Position analysis
            user_config: User configuration

        Returns:
            AIDecision if action needed, None otherwise
        """
        try:
            health_score = await self.position_sync.get_position_health_score(analysis)

            # Alert if health score is low
            if health_score < 50:
                decision = AIDecision(
                    decision_type="health_alert",
                    action_taken="Portfolio health degraded",
                    confidence=100.0 - health_score,
                    reasoning=f"Health score: {health_score:.1f}/100. "
                              f"Total P&L: {analysis.total_pnl:+.2f}, "
                              f"Positions: {analysis.total_positions}",
                    regime_at_decision="UNKNOWN",
                    vix_at_decision=0.0,
                    spot_at_decision=0.0,
                    indicators_snapshot=analysis.to_dict()
                )
                return decision

            return None

        except Exception as e:
            logger.error(f"Error evaluating position health: {e}")
            return None

    async def _evaluate_adjustment(
        self,
        strategy: Dict,
        user_config: AIUserConfig
    ) -> Optional[AIDecision]:
        """
        Evaluate if a strategy needs adjustment.

        Args:
            strategy: AutoPilot strategy data
            user_config: User configuration

        Returns:
            AIDecision if adjustment needed, None otherwise
        """
        try:
            strategy_id = strategy.get('id')
            strategy_type = strategy.get('strategy_type')
            current_pnl = strategy.get('current_pnl', 0)
            entry_time = strategy.get('entry_time')

            if not strategy_id:
                return None

            # Get AI adjustment advisor
            from app.services.ai.ai_adjustment_advisor import AIAdjustmentAdvisor
            advisor = AIAdjustmentAdvisor(self.kite, self.db)

            # Check if adjustment is needed based on multiple factors
            adjustment_triggers = []

            # 1. Check Delta imbalance (if position legs available)
            if 'position_legs' in strategy and strategy['position_legs']:
                total_delta = sum(leg.get('delta', 0) for leg in strategy['position_legs'])
                if abs(total_delta) > 0.3:  # Delta threshold
                    adjustment_triggers.append(f"Delta imbalance: {total_delta:.3f}")

            # 2. Check P&L targets
            target_profit = strategy.get('target_profit')
            max_loss = strategy.get('max_loss')

            if target_profit and current_pnl >= target_profit:
                adjustment_triggers.append(f"Profit target hit: {current_pnl:.2f} >= {target_profit:.2f}")

            if max_loss and current_pnl <= -abs(max_loss):
                adjustment_triggers.append(f"Max loss hit: {current_pnl:.2f} <= -{abs(max_loss):.2f}")

            # 3. Check regime mismatch
            if self._last_regime:
                strategy_regime = strategy.get('entry_regime')
                if strategy_regime and str(strategy_regime) != str(self._last_regime.regime_type):
                    adjustment_triggers.append(
                        f"Regime mismatch: entered in {strategy_regime}, now {self._last_regime.regime_type}"
                    )

            # 4. Check time decay exposure (for theta-heavy strategies)
            if entry_time:
                from datetime import datetime
                days_in_trade = (datetime.utcnow() - entry_time).days
                if days_in_trade >= 5:  # Arbitrary threshold
                    adjustment_triggers.append(f"Extended time in trade: {days_in_trade} days")

            # If any triggers found, create adjustment decision
            if adjustment_triggers:
                decision = AIDecision(
                    decision_type="adjustment",
                    action_taken="Adjustment recommended",
                    confidence=min(70.0 + len(adjustment_triggers) * 10, 95.0),
                    reasoning="; ".join(adjustment_triggers),
                    regime_at_decision=str(self._last_regime.regime_type) if self._last_regime else "UNKNOWN",
                    vix_at_decision=self._last_regime.indicators.vix if self._last_regime else 0.0,
                    spot_at_decision=self._last_regime.indicators.spot_price if self._last_regime else 0.0,
                    indicators_snapshot={
                        "strategy_id": strategy_id,
                        "strategy_type": strategy_type,
                        "current_pnl": current_pnl,
                        "triggers": adjustment_triggers
                    }
                )
                return decision

            return None

        except Exception as e:
            logger.error(f"Error evaluating adjustment: {e}")
            return None

    async def _log_decision(self, user_id: str, decision: AIDecision):
        """
        Log AI decision to database.

        Args:
            user_id: User ID
            decision: AI decision to log
        """
        # Placeholder for database logging
        # Real implementation would insert into ai_decisions_log table
        logger.info(f"AI Decision logged: {decision.decision_type} - {decision.action_taken}")


__all__ = ["AIMonitor", "AIDecision"]
