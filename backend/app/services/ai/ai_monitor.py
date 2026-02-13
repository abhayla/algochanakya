"""
AI Monitor Service

Monitors AI-managed AutoPilot strategies and makes intelligent decisions:
- Detects regime changes and suggests adjustments
- Evaluates position health
- Recommends entry/exit actions
- Logs all AI decisions with reasoning
- Autonomous drawdown control via risk state engine
- Extreme event detection (VIX spikes, API outages)

Integrates with the existing strategy_monitor.py for AutoPilot.
"""

import logging
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.ai import AIUserConfig
from app.models.ai_risk_state import RiskState
from app.services.ai.market_regime import MarketRegimeClassifier, RegimeType
from app.services.ai.strategy_recommender import StrategyRecommender
from app.services.ai.position_sync import PositionSyncService, PositionAnalysis
from app.services.ai.claude_advisor import ClaudeAdvisor
from app.services.ai.risk_state_engine import RiskStateEngine
from app.services.ai.extreme_event_handler import ExtremeEventHandler, ExtremeEventSeverity
from app.services.ai.stress_greeks_engine import StressGreeksEngine
from app.services.ai.websocket_health_monitor import get_health_monitor, CircuitBreakerState
from app.services.legacy.market_data import MarketDataService
from app.services.options.greeks_calculator import GreeksCalculatorService

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
        self.risk_state_engine = RiskStateEngine(db)
        self.extreme_event_handler = ExtremeEventHandler(db)
        self.market_data = MarketDataService(kite)
        self.market_data.set_extreme_event_handler(self.extreme_event_handler)
        self._last_regime: Optional[RegimeResponse] = None
        self._regime_change_threshold = 15.0  # % confidence change
        self._block_new_deployments = False  # Set by extreme events

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
            # Step -2: CIRCUIT BREAKER CHECK - Stop all AI trading if WebSocket health is poor
            health_monitor = get_health_monitor()
            if health_monitor:
                circuit_state = health_monitor.get_circuit_state()
                if circuit_state == CircuitBreakerState.OPEN:
                    logger.warning(f"AI trading paused for user {user_id} - WebSocket circuit breaker is OPEN")

                    # Create decision record for circuit breaker
                    metrics = health_monitor.get_health_summary()
                    circuit_decision = AIDecision(
                        decision_type="circuit_breaker",
                        action_taken="trading_paused",
                        confidence=100.0,
                        reasoning=f"WebSocket circuit breaker tripped. Health score: {metrics['health_score']:.1f}. Trading paused until connection recovers.",
                        regime_at_decision="UNKNOWN",
                        vix_at_decision=0,
                        spot_at_decision=0,
                        indicators_snapshot={
                            "circuit_state": circuit_state.value,
                            "health_score": metrics["health_score"],
                            "is_connected": metrics["is_connected"],
                            "sync_lag_seconds": metrics["sync_lag_seconds"],
                            "is_data_stale": metrics["is_data_stale"]
                        }
                    )
                    decisions.append(circuit_decision)
                    await self._log_decision(user_id, circuit_decision)
                    return decisions  # Skip all AI processing

                elif circuit_state == CircuitBreakerState.HALF_OPEN:
                    # Allow monitoring but block new deployments
                    self._block_new_deployments = True
                    logger.info(f"WebSocket in recovery mode - blocking new deployments for user {user_id}")

            # Skip if AI is not enabled
            if not user_config.ai_enabled:
                return decisions

            logger.debug(f"Processing AI strategies for user {user_id}")

            # Step -1: EXTREME EVENT DETECTION - Check for VIX spikes and API outages
            try:
                vix = await self.market_data.get_vix()
                extreme_events = await self.extreme_event_handler.detect_extreme_events(
                    vix=float(vix),
                    is_market_open=True
                )

                for event in extreme_events:
                    if event["severity"] == ExtremeEventSeverity.CRITICAL:
                        # Handle critical event (triggers kill switch)
                        # Note: kill_switch_service needs to be available
                        # For now, log critical event and let user handle manually
                        logger.critical(f"CRITICAL extreme event detected: {event['message']}")

                        # Send WebSocket alert if ws_manager is available
                        # ws_manager would need to be passed to this method

                        # Create decision record
                        critical_decision = AIDecision(
                            decision_type="extreme_event",
                            action_taken="critical_event_detected",
                            confidence=100.0,
                            reasoning=event["message"],
                            regime_at_decision="UNKNOWN",
                            vix_at_decision=float(vix),
                            spot_at_decision=0,
                            indicators_snapshot={
                                "event_type": event["type"].value,
                                "severity": event["severity"].value,
                                "value": event["value"],
                                "threshold": event["threshold"]
                            }
                        )
                        decisions.append(critical_decision)

                        # Log decision
                        await self._log_decision(user_id, critical_decision)

                        # Block new deployments and return early
                        self._block_new_deployments = True
                        return decisions

                    elif event["severity"] == ExtremeEventSeverity.ELEVATED:
                        # Alert and block new deployments
                        logger.warning(f"Extreme event detected: {event['message']}")

                        # Create decision record
                        elevated_decision = AIDecision(
                            decision_type="extreme_event",
                            action_taken="elevated_event_detected",
                            confidence=90.0,
                            reasoning=event["message"],
                            regime_at_decision="UNKNOWN",
                            vix_at_decision=float(vix),
                            spot_at_decision=0,
                            indicators_snapshot={
                                "event_type": event["type"].value,
                                "severity": event["severity"].value,
                                "value": event["value"],
                                "threshold": event["threshold"]
                            }
                        )
                        decisions.append(elevated_decision)

                        # Continue monitoring but block new deployments
                        self._block_new_deployments = True

            except Exception as e:
                logger.error(f"Error checking extreme events: {e}")
                # Continue processing even if extreme event check fails (fail-open pattern)

            # Step 0: AUTONOMOUS DRAWDOWN CONTROL - Evaluate risk state
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            recommended_state, reason = await self.risk_state_engine.evaluate_state(user_uuid)
            current_risk_state = await self.risk_state_engine.get_current_state(user_uuid)

            # Transition state if needed
            if recommended_state != RiskState(current_risk_state.state):
                logger.warning(
                    f"Risk state transition recommended for user {user_id}: "
                    f"{current_risk_state.state} -> {recommended_state.value}. Reason: {reason}"
                )

                # Get performance metrics for transition
                sharpe, drawdown, consecutive_losses = await self.risk_state_engine._get_performance_metrics(user_uuid)

                # Perform transition
                await self.risk_state_engine.transition_state(
                    user_id=user_uuid,
                    new_state=recommended_state,
                    reason=reason,
                    sharpe_ratio=sharpe,
                    drawdown=drawdown,
                    consecutive_losses=consecutive_losses
                )

                # Log decision
                risk_decision = AIDecision(
                    decision_type="risk_state_transition",
                    action_taken=f"Transitioned to {recommended_state.value}",
                    confidence=100.0,
                    reasoning=reason,
                    regime_at_decision="UNKNOWN",
                    vix_at_decision=0.0,
                    spot_at_decision=0.0,
                    indicators_snapshot={
                        "new_state": recommended_state.value,
                        "previous_state": current_risk_state.state,
                        "sharpe_ratio": sharpe,
                        "drawdown": float(drawdown) if drawdown else None,
                        "consecutive_losses": consecutive_losses
                    }
                )
                decisions.append(risk_decision)

                # Update current_risk_state for subsequent checks
                current_risk_state = await self.risk_state_engine.get_current_state(user_uuid)

            # Apply DEGRADED mode adjustments if needed
            if RiskState(current_risk_state.state) == RiskState.DEGRADED:
                logger.info(f"User {user_id} is in DEGRADED risk state. Applying conservative adjustments.")
                # Adjustments will be applied in deployment logic

            # Block new deployments if PAUSED
            if RiskState(current_risk_state.state) == RiskState.PAUSED:
                logger.warning(f"User {user_id} is in PAUSED risk state. Blocking all new deployments.")
                # Return early - no new deployments allowed
                pause_decision = AIDecision(
                    decision_type="deployment_blocked",
                    action_taken="Blocked new deployment due to PAUSED risk state",
                    confidence=100.0,
                    reasoning=current_risk_state.reason or "Risk state is PAUSED",
                    regime_at_decision="UNKNOWN",
                    vix_at_decision=0.0,
                    spot_at_decision=0.0,
                    indicators_snapshot={
                        "risk_state": current_risk_state.state,
                        "drawdown": float(current_risk_state.current_drawdown) if current_risk_state.current_drawdown else None
                    }
                )
                decisions.append(pause_decision)

                # Log and return early
                for decision in decisions:
                    await self._log_decision(user_id, decision)
                return decisions

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

    async def evaluate_stress_risk_for_deployment(
        self,
        user_id: str,
        user_config: AIUserConfig,
        portfolio_legs: List[Dict[str, Any]],
        new_strategy_legs: List[Dict[str, Any]],
        current_spot: float,
        lot_size: int = 1
    ) -> Dict[str, Any]:
        """
        Evaluate stress risk before deploying a new strategy (Priority 1.1).

        Args:
            user_id: User ID
            user_config: User configuration with stress limits
            portfolio_legs: Current portfolio position legs
            new_strategy_legs: New strategy legs to deploy
            current_spot: Current spot price
            lot_size: Lot size for the underlying

        Returns:
            Dict with:
                - acceptable: bool (whether deployment is acceptable)
                - stress_risk_score: float (combined stress risk score)
                - violations: List[str] (reasons for rejection if not acceptable)
                - portfolio_stress: StressTestResult
                - new_strategy_stress: StressTestResult
        """
        try:
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            # Create GreeksCalculatorService
            greeks_calculator = GreeksCalculatorService(self.db, user_uuid)

            # Create StressGreeksEngine
            stress_engine = StressGreeksEngine(greeks_calculator)

            # Calculate stress scenarios for current portfolio
            portfolio_stress = await stress_engine.calculate_stress_scenarios(
                legs=portfolio_legs,
                current_spot=current_spot,
                lot_size=lot_size
            )

            # Calculate stress scenarios for new strategy
            new_strategy_stress = await stress_engine.calculate_stress_scenarios(
                legs=new_strategy_legs,
                current_spot=current_spot,
                lot_size=lot_size
            )

            # Evaluate deployment risk
            result = stress_engine.evaluate_deployment_risk(
                portfolio_stress_result=portfolio_stress,
                new_strategy_stress_result=new_strategy_stress,
                max_stress_risk_score=float(user_config.max_stress_risk_score),
                max_portfolio_delta=float(user_config.max_portfolio_delta),
                max_portfolio_gamma=float(user_config.max_portfolio_gamma)
            )

            # Log result
            if not result['acceptable']:
                logger.warning(
                    f"Deployment blocked for user {user_id} due to stress risk: {result['violations']}"
                )
            else:
                logger.info(
                    f"Deployment acceptable for user {user_id}. "
                    f"Combined stress risk score: {result['combined_stress_risk_score']:.2f}"
                )

            # Add stress test results to response
            result['portfolio_stress'] = portfolio_stress
            result['new_strategy_stress'] = new_strategy_stress

            return result

        except Exception as e:
            logger.error(f"Error evaluating stress risk for deployment: {e}")
            # Fail-open: allow deployment if stress calculation fails
            return {
                'acceptable': True,
                'stress_risk_score': 0.0,
                'violations': [],
                'error': str(e),
                'fail_open': True
            }


__all__ = ["AIMonitor", "AIDecision"]
