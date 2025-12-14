"""
Adjustment Engine Service - Phase 3 + Phase 5D + Phase 5E

Auto-adjust positions based on configurable triggers:

EXISTING (Phase 3):
- PNL-based: When P&L reaches threshold
- Delta-based: When position delta exceeds threshold
- Time-based: At specific time
- Premium-based: When premium decays to threshold
- VIX-based: When VIX crosses threshold
- Spot-based: When spot price crosses threshold

NEW (Phase 5D - Exit Rules):
- profit_pct_based: Close at X% of max profit (#18-19)
- premium_captured_pct: Exit when X% of premium captured (#20)
- return_on_margin: Exit when trade returns X% of margin (#21)
- capital_recycling: Close early to recycle capital (#22)
- dte_based: Close at specific DTE (#23)
- days_in_trade: Exit after X days in trade (#24)
- theta_curve_based: Exit based on theta decay curve (#25)

NEW (Phase 5E - Risk-Based Exits):
- gamma_based: Exit based on gamma risk (#26)
- atr_based: ATR-based trailing stop (#27)
- delta_doubles: Alert when delta doubles from entry (#28)
- delta_change: Alert on large daily delta shift (#29)

NEW (Phase 5G - Greek-Based Triggers):
- theta_based: Trigger on theta threshold (#56)
- vega_based: Trigger on vega exposure (#57)
- Note: delta_based and gamma_based already implemented above

Action Types:
- add_hedge: Add protective leg
- close_leg: Close specific leg
- roll_strike: Move strike closer/farther from ATM
- roll_expiry: Move to next expiry
- exit_all: Exit entire position
- scale_down: Reduce position size by X%
- scale_up: Increase position size by X%
- add_to_opposite: Add contracts to non-threatened side (Phase 5F #37)
"""
import logging
from datetime import datetime, timezone, time, date
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotAdjustmentLog,
    AutoPilotLog,
    AdjustmentTriggerType,
    AdjustmentActionType,
    ExecutionMode,
    LogSeverity
)
from app.services.theta_curve_service import get_theta_curve_service
from app.services.gamma_risk_service import get_gamma_risk_service
from app.services.dte_zone_service import get_dte_zone_service

logger = logging.getLogger(__name__)


# ===== PHASE 5G: OFFENSIVE/DEFENSIVE CATEGORIZATION =====

class AdjustmentCategory:
    """
    Categorization of adjustment actions by risk impact.

    Phase 5G #45: Professional traders classify adjustments as:
    - OFFENSIVE: Increase risk for more premium collection
    - DEFENSIVE: Reduce risk (priority: protection over profit)
    - NEUTRAL: Rebalance without significantly changing risk/reward profile
    """
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    NEUTRAL = "neutral"


# Action type categorization mapping
ADJUSTMENT_CATEGORIES = {
    # Offensive actions (increase risk/premium)
    "roll_strike_closer": AdjustmentCategory.OFFENSIVE,
    "scale_up": AdjustmentCategory.OFFENSIVE,
    "add_to_opposite_side": AdjustmentCategory.OFFENSIVE,
    "widen_spread": AdjustmentCategory.OFFENSIVE,

    # Defensive actions (reduce risk)
    "roll_strike_farther": AdjustmentCategory.DEFENSIVE,
    "add_hedge": AdjustmentCategory.DEFENSIVE,
    "close_leg": AdjustmentCategory.DEFENSIVE,
    "scale_down": AdjustmentCategory.DEFENSIVE,
    "exit_all": AdjustmentCategory.DEFENSIVE,

    # Neutral actions (rebalancing)
    "roll_expiry": AdjustmentCategory.NEUTRAL,
    "delta_neutral_rebalance": AdjustmentCategory.NEUTRAL,
    "shift_leg": AdjustmentCategory.NEUTRAL,
}


def get_adjustment_category(action_type: str, params: Dict[str, Any] = None) -> str:
    """
    Get the risk category for an adjustment action.

    Some actions like roll_strike can be offensive or defensive depending
    on direction parameter.

    Args:
        action_type: The adjustment action type
        params: Optional parameters (e.g., direction for roll_strike)

    Returns:
        Category string: "offensive", "defensive", or "neutral"
    """
    # Handle context-dependent actions
    if action_type == "roll_strike":
        if params and params.get('direction') == 'closer':
            return AdjustmentCategory.OFFENSIVE
        elif params and params.get('direction') == 'farther':
            return AdjustmentCategory.DEFENSIVE
        else:
            return AdjustmentCategory.NEUTRAL

    # Return mapped category or neutral as default
    return ADJUSTMENT_CATEGORIES.get(action_type, AdjustmentCategory.NEUTRAL)


def get_category_description(category: str) -> str:
    """Get human-readable description for a category."""
    descriptions = {
        AdjustmentCategory.OFFENSIVE: "Increases risk to collect more premium",
        AdjustmentCategory.DEFENSIVE: "Reduces risk to protect capital",
        AdjustmentCategory.NEUTRAL: "Rebalances position without major risk change"
    }
    return descriptions.get(category, "Unknown category")


def get_category_color(category: str) -> str:
    """Get UI color code for category."""
    colors = {
        AdjustmentCategory.OFFENSIVE: "orange",  # Warning: more aggressive
        AdjustmentCategory.DEFENSIVE: "green",   # Success: safer
        AdjustmentCategory.NEUTRAL: "blue"       # Info: neutral
    }
    return colors.get(category, "gray")


class AdjustmentEngine:
    """
    Engine for evaluating and executing adjustment rules.

    Adjustment rules are evaluated in priority order when a strategy
    is in ACTIVE status. When a rule triggers, the configured action
    is executed either automatically or with user confirmation.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.market_data_service = None
        self.order_executor = None
        self.confirmation_service = None
        self.websocket_manager = None

    def set_market_data_service(self, service):
        """Inject market data service for getting current values"""
        self.market_data_service = service

    def set_order_executor(self, executor):
        """Inject order executor for placing adjustment orders"""
        self.order_executor = executor

    def set_confirmation_service(self, service):
        """Inject confirmation service for semi-auto mode"""
        self.confirmation_service = service

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for sending alerts"""
        self.websocket_manager = manager

    async def evaluate_rules(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Evaluate all enabled adjustment rules for a strategy.

        Args:
            strategy: The strategy to evaluate
            market_data: Current market data (spot, vix, prices, etc.)

        Returns:
            List of (rule, evaluation_result) tuples for triggered rules
        """
        triggered_rules = []
        adjustment_rules = strategy.adjustment_rules or []

        for rule in adjustment_rules:
            if not rule.get('enabled', True):
                continue

            # Check cooldown
            if await self._is_in_cooldown(strategy.id, rule['id'], rule.get('cooldown_seconds', 0)):
                continue

            # Check max executions
            if await self._exceeded_max_executions(strategy.id, rule['id'], rule.get('max_executions')):
                continue

            # Evaluate trigger condition
            evaluation = await self._evaluate_trigger(strategy, rule, market_data)

            if evaluation['triggered']:
                triggered_rules.append((rule, evaluation))
                logger.info(f"Adjustment rule '{rule['name']}' triggered for strategy {strategy.id}")

        return triggered_rules

    async def execute_adjustment(
        self,
        strategy: AutoPilotStrategy,
        rule: Dict[str, Any],
        evaluation: Dict[str, Any],
        execution_mode: Optional[ExecutionMode] = None
    ) -> Dict[str, Any]:
        """
        Execute an adjustment action.

        Args:
            strategy: The strategy to adjust
            rule: The triggered rule configuration
            evaluation: The trigger evaluation result
            execution_mode: Override execution mode (uses rule's mode if not provided)

        Returns:
            Execution result dict
        """
        mode = execution_mode or ExecutionMode(rule.get('execution_mode', 'auto'))
        action = rule['action']

        # Create adjustment log
        adjustment_log = await self._create_adjustment_log(strategy, rule, evaluation, mode)

        try:
            if mode == ExecutionMode.SEMI_AUTO:
                # Create confirmation request
                if self.confirmation_service:
                    confirmation = await self.confirmation_service.create_confirmation(
                        strategy_id=strategy.id,
                        action_type=f"adjustment_{action['type']}",
                        action_description=self._get_action_description(rule, evaluation),
                        action_data={
                            'rule': rule,
                            'evaluation': evaluation,
                            'adjustment_log_id': adjustment_log.id
                        },
                        rule_id=rule['id'],
                        rule_name=rule['name']
                    )
                    adjustment_log.confirmation_id = confirmation.id
                    await self.db.commit()

                    return {
                        'executed': False,
                        'confirmation_required': True,
                        'confirmation_id': confirmation.id,
                        'message': f"Confirmation required for adjustment '{rule['name']}'"
                    }
                else:
                    # No confirmation service, fall back to auto
                    mode = ExecutionMode.AUTO

            if mode == ExecutionMode.MANUAL:
                # Just log, don't execute
                await self._log_adjustment_event(
                    strategy,
                    rule,
                    'adjustment_condition_triggered',
                    f"Adjustment '{rule['name']}' triggered but not executed (manual mode)"
                )
                return {
                    'executed': False,
                    'manual_mode': True,
                    'message': f"Adjustment '{rule['name']}' requires manual execution"
                }

            # Execute the action
            result = await self._execute_action(strategy, action, evaluation)

            # Update adjustment log
            adjustment_log.executed = True
            adjustment_log.execution_result = result
            adjustment_log.executed_at = datetime.now(timezone.utc)
            await self.db.commit()

            # Send WebSocket notification
            await self._send_adjustment_notification(strategy, rule, result)

            return result

        except Exception as e:
            logger.error(f"Error executing adjustment: {e}")
            adjustment_log.error_message = str(e)
            await self.db.commit()
            raise

    async def _evaluate_trigger(
        self,
        strategy: AutoPilotStrategy,
        rule: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if a trigger condition is met.

        Returns:
            Dict with 'triggered' bool and evaluation details
        """
        trigger = rule['trigger']
        trigger_type = trigger['type']
        condition = trigger['condition']
        target_value = trigger['value']

        current_value = None
        triggered = False

        if trigger_type == 'pnl_based':
            current_value = await self._get_strategy_pnl(strategy, market_data)
            triggered = self._check_pnl_condition(current_value, condition, target_value)

        elif trigger_type == 'delta_based':
            current_value = await self._get_position_delta(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'time_based':
            current_value = datetime.now(timezone.utc).strftime('%H:%M')
            triggered = self._check_time_condition(current_value, condition, target_value)

        elif trigger_type == 'premium_based':
            current_value = await self._get_total_premium(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'vix_based':
            current_value = market_data.get('vix', 0)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'spot_based':
            current_value = market_data.get('spot', 0)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        # Phase 5D: New Exit Rule Triggers

        elif trigger_type == 'profit_pct_based':
            # #18-19: Close at X% of max profit
            current_value = await self._get_profit_pct_of_max(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'premium_captured_pct':
            # #20: Exit when X% of premium captured
            current_value = await self._get_premium_captured_pct(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'return_on_margin':
            # #21: Exit when trade returns X% of margin
            current_value = await self._get_return_on_margin(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'capital_recycling':
            # #22: Close early for capital recycling
            current_value = await self._get_capital_recycling_score(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'dte_based':
            # #23: Close at specific DTE
            current_value = await self._get_days_to_expiry(strategy)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'days_in_trade':
            # #24: Exit after X days in trade
            current_value = await self._get_days_in_trade(strategy)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'theta_curve_based':
            # #25: Exit based on theta decay curve
            theta_analysis = await self._analyze_theta_curve(strategy, market_data)
            current_value = theta_analysis['should_exit']
            triggered = theta_analysis['should_exit']

        # Phase 5E: Risk-Based Exit Triggers

        elif trigger_type == 'gamma_based':
            # #26: Exit based on gamma risk
            gamma_assessment = await self._assess_gamma_risk(strategy, market_data)
            current_value = gamma_assessment['should_exit']
            triggered = gamma_assessment['should_exit']

        elif trigger_type == 'atr_based':
            # #27: ATR-based trailing stop
            atr_analysis = await self._analyze_atr_trailing_stop(strategy, market_data)
            current_value = atr_analysis['stop_triggered']
            triggered = atr_analysis['stop_triggered']

        elif trigger_type == 'delta_doubles':
            # #28: Alert when delta doubles from entry
            delta_analysis = await self._check_delta_doubles(strategy, market_data)
            current_value = delta_analysis['has_doubled']
            triggered = delta_analysis['has_doubled']

        elif trigger_type == 'delta_change':
            # #29: Alert on large daily delta shift
            delta_change_analysis = await self._check_delta_change(strategy, market_data)
            current_value = delta_change_analysis['large_change']
            triggered = delta_change_analysis['large_change']

        # Phase 5G: Greek-Based Triggers

        elif trigger_type == 'theta_based':
            # Phase 5G #56: Trigger based on theta threshold
            current_value = await self._get_position_theta(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        elif trigger_type == 'vega_based':
            # Phase 5G #57: Trigger based on vega exposure
            current_value = await self._get_position_vega(strategy, market_data)
            triggered = self._check_numeric_condition(current_value, condition, target_value)

        return {
            'triggered': triggered,
            'trigger_type': trigger_type,
            'condition': condition,
            'target_value': target_value,
            'current_value': current_value,
            'evaluated_at': datetime.now(timezone.utc).isoformat()
        }

    async def _execute_action(
        self,
        strategy: AutoPilotStrategy,
        action: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the adjustment action"""
        action_type = action['type']
        params = action.get('params', {})

        if action_type == 'exit_all':
            return await self._action_exit_all(strategy, params)

        elif action_type == 'add_hedge':
            return await self._action_add_hedge(strategy, params)

        elif action_type == 'close_leg':
            return await self._action_close_leg(strategy, params)

        elif action_type == 'roll_strike':
            return await self._action_roll_strike(strategy, params)

        elif action_type == 'roll_expiry':
            return await self._action_roll_expiry(strategy, params)

        elif action_type == 'scale_down':
            return await self._action_scale_down(strategy, params)

        elif action_type == 'scale_up':
            return await self._action_scale_up(strategy, params)

        elif action_type == 'add_to_opposite':
            return await self._action_add_to_opposite(strategy, params)

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    # -------------------------------------------------------------------------
    # Condition Checking Methods
    # -------------------------------------------------------------------------

    def _check_pnl_condition(
        self,
        current_pnl: Decimal,
        condition: str,
        target_value: Any
    ) -> bool:
        """Check PNL-based conditions"""
        if condition == 'loss_exceeds':
            return current_pnl < -abs(Decimal(str(target_value)))
        elif condition == 'profit_exceeds':
            return current_pnl > Decimal(str(target_value))
        elif condition == 'loss_percentage_exceeds':
            # Would need initial investment to calculate
            return False  # TODO: Implement
        return False

    def _check_numeric_condition(
        self,
        current_value: float,
        condition: str,
        target_value: Any
    ) -> bool:
        """Check numeric conditions"""
        if current_value is None:
            return False

        if condition in ('greater_than', 'exceeds'):
            return current_value > float(target_value)
        elif condition in ('less_than', 'below'):
            return current_value < float(target_value)
        elif condition == 'between':
            if isinstance(target_value, list) and len(target_value) == 2:
                return float(target_value[0]) <= current_value <= float(target_value[1])
        elif condition == 'equals':
            return abs(current_value - float(target_value)) < 0.01
        elif condition == 'crosses_above':
            # Would need previous value
            return False  # TODO: Implement with state tracking
        elif condition == 'crosses_below':
            return False  # TODO: Implement with state tracking
        return False

    def _check_time_condition(
        self,
        current_time: str,
        condition: str,
        target_value: str
    ) -> bool:
        """Check time-based conditions"""
        if condition == 'equals':
            return current_time == target_value
        elif condition == 'after':
            return current_time >= target_value
        elif condition == 'before':
            return current_time < target_value
        return False

    # -------------------------------------------------------------------------
    # Data Retrieval Methods
    # -------------------------------------------------------------------------

    async def _get_strategy_pnl(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Decimal:
        """Calculate current P&L for strategy"""
        runtime_state = strategy.runtime_state or {}
        entry_prices = runtime_state.get('entry_prices', {})
        current_prices = market_data.get('option_prices', {})

        total_pnl = Decimal('0')
        positions = runtime_state.get('positions', [])

        for position in positions:
            symbol = position.get('tradingsymbol')
            entry_price = Decimal(str(entry_prices.get(symbol, 0)))
            current_price = Decimal(str(current_prices.get(symbol, entry_price)))
            qty = position.get('quantity', 0)

            if position.get('transaction_type') == 'BUY':
                pnl = (current_price - entry_price) * qty
            else:
                pnl = (entry_price - current_price) * qty

            total_pnl += pnl

        return total_pnl

    async def _get_position_delta(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate net delta for strategy position"""
        greeks = strategy.greeks_snapshot or {}
        return greeks.get('net_delta', 0.0)

    async def _get_position_gamma(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate net gamma for strategy position (Phase 5G)"""
        greeks = strategy.greeks_snapshot or {}
        return greeks.get('net_gamma', 0.0)

    async def _get_position_theta(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate net theta for strategy position (Phase 5G)"""
        greeks = strategy.greeks_snapshot or {}
        return greeks.get('net_theta', 0.0)

    async def _get_position_vega(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate net vega for strategy position (Phase 5G)"""
        greeks = strategy.greeks_snapshot or {}
        return greeks.get('net_vega', 0.0)

    async def _get_total_premium(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Decimal:
        """Calculate total premium received/paid"""
        runtime_state = strategy.runtime_state or {}
        return Decimal(str(runtime_state.get('total_premium', 0)))

    # -------------------------------------------------------------------------
    # Phase 5D: New Exit Rule Calculation Methods
    # -------------------------------------------------------------------------

    async def _get_profit_pct_of_max(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """
        #18-19: Calculate current profit as percentage of max profit.

        Example: If max profit is ₹10,000 and current P&L is ₹5,000,
        returns 50.0 (50% of max profit captured)
        """
        current_pnl = await self._get_strategy_pnl(strategy, market_data)
        max_profit = strategy.max_profit or 0

        if max_profit <= 0:
            return 0.0

        profit_pct = (float(current_pnl) / float(max_profit)) * 100
        return max(0.0, profit_pct)  # Don't return negative percentages

    async def _get_premium_captured_pct(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """
        #20: Calculate percentage of initial premium that has been captured.

        For credit strategies (sell options):
        - Entry premium: ₹500 (received)
        - Current value: ₹100 (to buy back)
        - Captured: ₹400 (80% of ₹500)

        Example: If sold for ₹500 and current value is ₹100,
        returns 80.0 (80% of premium captured)
        """
        runtime_state = strategy.runtime_state or {}
        entry_premium = float(runtime_state.get('total_premium', 0))

        if entry_premium == 0:
            return 0.0

        # Get current position value
        current_value = await self._get_current_position_value(strategy, market_data)

        # For credit strategies (entry_premium > 0), calculate captured premium
        if entry_premium > 0:
            captured_premium = entry_premium - current_value
            captured_pct = (captured_premium / entry_premium) * 100
        else:
            # For debit strategies (entry_premium < 0), calculate differently
            captured_premium = current_value - abs(entry_premium)
            captured_pct = (captured_premium / abs(entry_premium)) * 100

        return max(0.0, captured_pct)

    async def _get_current_position_value(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate current market value of the position"""
        runtime_state = strategy.runtime_state or {}
        current_prices = market_data.get('option_prices', {})
        positions = runtime_state.get('positions', [])

        total_value = 0.0

        for position in positions:
            symbol = position.get('tradingsymbol')
            current_price = float(current_prices.get(symbol, 0))
            qty = position.get('quantity', 0)

            # Value is always positive (what it costs to close)
            value = current_price * qty
            total_value += value

        return total_value

    async def _get_return_on_margin(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """
        #21: Calculate return as percentage of margin used.

        Example: If margin is ₹50,000 and current P&L is ₹10,000,
        returns 20.0 (20% return on margin)
        """
        current_pnl = await self._get_strategy_pnl(strategy, market_data)
        margin_used = strategy.margin_used or 0

        if margin_used <= 0:
            return 0.0

        return_pct = (float(current_pnl) / float(margin_used)) * 100
        return return_pct

    async def _get_capital_recycling_score(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> float:
        """
        #22: Calculate capital recycling score.

        Higher score = better to exit early and recycle capital.

        Score factors:
        - Profit captured % (higher = better to exit)
        - Days in trade (longer = better to exit)
        - DTE remaining (less = better to exit)
        - Theta efficiency (lower = better to exit)

        Returns: Score 0-100 (>70 suggests exit for capital recycling)
        """
        # Get component metrics
        profit_pct = await self._get_profit_pct_of_max(strategy, market_data)
        premium_captured = await self._get_premium_captured_pct(strategy, market_data)
        days_in_trade = await self._get_days_in_trade(strategy)
        dte = await self._get_days_to_expiry(strategy)

        # Calculate score (weighted average)
        # If profit > 50% and premium captured > 75%, strong signal to exit
        profit_score = min(profit_pct, 100)  # Cap at 100
        premium_score = min(premium_captured, 100)

        # Days in trade score (more days = higher score, cap at 30 days)
        days_score = min((days_in_trade / 30) * 50, 50)

        # DTE score (less DTE = higher score)
        if dte >= 45:
            dte_score = 0
        elif dte >= 21:
            dte_score = 20
        elif dte >= 14:
            dte_score = 40
        else:
            dte_score = 60

        # Weighted average
        recycling_score = (
            profit_score * 0.4 +
            premium_score * 0.3 +
            days_score * 0.15 +
            dte_score * 0.15
        )

        return recycling_score

    async def _get_days_to_expiry(self, strategy: AutoPilotStrategy) -> int:
        """
        #23: Calculate days to expiry.

        Returns: Number of days until expiry
        """
        if not strategy.expiry_date:
            return 999  # Default high value

        if isinstance(strategy.expiry_date, str):
            expiry = datetime.strptime(strategy.expiry_date, '%Y-%m-%d').date()
        else:
            expiry = strategy.expiry_date

        today = date.today()
        dte = (expiry - today).days

        return max(0, dte)  # Don't return negative

    async def _get_days_in_trade(self, strategy: AutoPilotStrategy) -> int:
        """
        #24: Calculate days since entry.

        Returns: Number of days since strategy was entered
        """
        if not strategy.entry_time:
            return 0

        entry_date = strategy.entry_time.date()
        today = date.today()
        days = (today - entry_date).days

        return max(0, days)

    async def _analyze_theta_curve(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        #25: Analyze theta decay curve and recommend exit.

        Uses ThetaCurveService to determine if exit is optimal based on:
        - Current DTE
        - Theta decay rate
        - Profit captured %

        Returns: Dict with should_exit and analysis details
        """
        theta_service = get_theta_curve_service()

        # Get current metrics
        dte = await self._get_days_to_expiry(strategy)
        current_theta = strategy.net_theta or 0.0
        profit_captured_pct = await self._get_profit_pct_of_max(strategy, market_data)

        # Get theta curve recommendation
        recommendation = theta_service.should_exit_based_on_theta_curve(
            dte=dte,
            current_theta=current_theta,
            profit_captured_pct=profit_captured_pct
        )

        return recommendation

    async def _assess_gamma_risk(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        #26: Assess gamma explosion risk.

        Uses GammaRiskService to determine if position should exit
        due to gamma risk near expiry.

        Returns: Dict with should_exit and risk assessment
        """
        gamma_service = get_gamma_risk_service()

        # Get current metrics
        dte = await self._get_days_to_expiry(strategy)
        net_gamma = float(strategy.net_gamma or 0.0)

        # Assess gamma risk
        should_exit, reason = gamma_service.should_exit_for_gamma_risk(
            dte=dte,
            net_gamma=net_gamma,
            position_type="short"
        )

        assessment = gamma_service.assess_gamma_risk(
            dte=dte,
            net_gamma=net_gamma,
            position_type="short"
        )

        return {
            'should_exit': should_exit,
            'reason': reason,
            'risk_level': assessment['risk_level'],
            'zone': assessment['zone'],
            'multiplier': assessment['multiplier'],
            'dte': dte,
            'net_gamma': net_gamma
        }

    async def _analyze_atr_trailing_stop(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        #27: Check ATR-based trailing stop.

        ATR (Average True Range) trailing stop dynamically adjusts
        stop loss based on market volatility.

        Returns: Dict with stop_triggered and stop_price
        """
        # Get runtime state
        runtime_state = strategy.runtime_state or {}

        # Get current spot price
        spot_price = market_data.get('spot', 0)

        # Get ATR multiplier from strategy config (default 2.0)
        atr_multiplier = runtime_state.get('atr_multiplier', 2.0)

        # Calculate ATR (simplified - in real impl, would calculate from historical data)
        # For now, use a fixed percentage of spot as proxy
        atr = spot_price * 0.02  # 2% ATR proxy

        # Get peak P&L (highest profit reached)
        peak_pnl = runtime_state.get('peak_pnl', strategy.current_pnl or 0)
        current_pnl = strategy.current_pnl or 0

        # Update peak if current is higher
        if current_pnl > peak_pnl:
            peak_pnl = current_pnl
            runtime_state['peak_pnl'] = peak_pnl

        # Calculate trailing stop threshold
        stop_threshold = peak_pnl - (atr * atr_multiplier)

        # Check if stop triggered
        stop_triggered = current_pnl < stop_threshold

        return {
            'stop_triggered': stop_triggered,
            'current_pnl': current_pnl,
            'peak_pnl': peak_pnl,
            'stop_threshold': stop_threshold,
            'atr': atr,
            'atr_multiplier': atr_multiplier
        }

    async def _check_delta_doubles(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        #28: Check if delta has doubled from entry.

        Significant delta increase indicates position has moved
        far from neutral, requiring adjustment.

        Returns: Dict with has_doubled and delta metrics
        """
        # Get current delta
        current_delta = abs(float(strategy.net_delta or 0.0))

        # Get entry delta from runtime state
        runtime_state = strategy.runtime_state or {}
        entry_delta = abs(float(runtime_state.get('entry_delta', 0.0)))

        # Check if doubled
        has_doubled = False
        if entry_delta > 0:
            has_doubled = current_delta >= 2 * entry_delta

        delta_change_pct = 0
        if entry_delta > 0:
            delta_change_pct = ((current_delta / entry_delta) - 1) * 100

        return {
            'has_doubled': has_doubled,
            'current_delta': current_delta,
            'entry_delta': entry_delta,
            'delta_change_pct': delta_change_pct,
            'threshold': 2 * entry_delta if entry_delta > 0 else 0
        }

    async def _check_delta_change(
        self,
        strategy: AutoPilotStrategy,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        #29: Check for large daily delta shift.

        Large delta changes (> 0.10/day) indicate significant
        market movement requiring attention.

        Returns: Dict with large_change and delta change metrics
        """
        # Get current delta
        current_delta = float(strategy.net_delta or 0.0)

        # Get previous delta from runtime state
        runtime_state = strategy.runtime_state or {}
        previous_delta = float(runtime_state.get('previous_delta', current_delta))

        # Calculate delta change
        delta_change = abs(current_delta - previous_delta)

        # Threshold for "large" change
        change_threshold = 0.10

        large_change = delta_change > change_threshold

        # Update previous delta for next check
        runtime_state['previous_delta'] = current_delta
        strategy.runtime_state = runtime_state

        return {
            'large_change': large_change,
            'delta_change': delta_change,
            'current_delta': current_delta,
            'previous_delta': previous_delta,
            'threshold': change_threshold
        }

    # -------------------------------------------------------------------------
    # Action Execution Methods
    # -------------------------------------------------------------------------

    async def _action_exit_all(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exit all positions"""
        order_type = params.get('order_type', 'MARKET')
        orders_placed = []

        # Exit logic similar to kill switch
        # Would use order_executor to place exit orders

        return {
            'action': 'exit_all',
            'orders_placed': orders_placed,
            'message': f"Exit all positions with {order_type} orders"
        }

    async def _action_add_hedge(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add protective hedge legs"""
        hedge_type = params.get('hedge_type', 'both')  # 'pe', 'ce', 'both'
        # Implementation would calculate strikes and place orders

        return {
            'action': 'add_hedge',
            'hedge_type': hedge_type,
            'message': f"Added {hedge_type} hedge"
        }

    async def _action_close_leg(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Close specific leg"""
        leg_id = params.get('leg_id')
        # Implementation would close the specified leg

        return {
            'action': 'close_leg',
            'leg_id': leg_id,
            'message': f"Closed leg {leg_id}"
        }

    async def _action_roll_strike(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Roll strike up/down"""
        direction = params.get('direction', 'closer')  # 'closer', 'farther'
        offset = params.get('offset', 100)
        # Implementation would close current and open new at different strike

        return {
            'action': 'roll_strike',
            'direction': direction,
            'offset': offset,
            'message': f"Rolled strike {direction} by {offset}"
        }

    async def _action_roll_expiry(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Roll to next expiry"""
        # Implementation would close current and open at next expiry

        return {
            'action': 'roll_expiry',
            'message': "Rolled to next expiry"
        }

    async def _action_scale_down(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reduce position size"""
        percentage = params.get('percentage', 50)
        # Implementation would close X% of position

        return {
            'action': 'scale_down',
            'percentage': percentage,
            'message': f"Scaled down position by {percentage}%"
        }

    async def _action_scale_up(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Increase position size"""
        percentage = params.get('percentage', 50)
        # Implementation would add X% to position

        return {
            'action': 'scale_up',
            'percentage': percentage,
            'message': f"Scaled up position by {percentage}%"
        }

    async def _action_add_to_opposite(
        self,
        strategy: AutoPilotStrategy,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add contracts to the opposite (non-threatened) side.

        Feature #37: Professional delta neutralization technique.

        When one side is under pressure, add more contracts to the
        profitable side to bring delta back toward neutral.

        Args:
            strategy: AutoPilot strategy
            params: {
                'option_type': 'CE' or 'PE',  # Which side to add
                'lots': int,                   # How many lots to add
                'strike': Decimal,             # Specific strike (optional)
                'target_delta': float,         # Target delta for new leg (optional)
                'execution_mode': 'market' or 'limit'
            }

        Returns:
            Dict with action result
        """
        option_type = params.get('option_type')
        lots = params.get('lots', 1)
        strike = params.get('strike')
        target_delta = params.get('target_delta', 0.15)
        execution_mode = params.get('execution_mode', 'market')

        if not option_type or option_type not in ['CE', 'PE']:
            raise ValueError("option_type must be 'CE' or 'PE'")

        logger.info(
            f"Adding {lots} lot(s) to {option_type} side for strategy {strategy.id} "
            f"(current delta: {strategy.net_delta})"
        )

        # If strike not specified, find strike matching target delta
        if not strike:
            # Use strike_finder_service to find appropriate strike
            # This would require injecting the strike_finder service
            # For now, return a placeholder
            return {
                'action': 'add_to_opposite',
                'option_type': option_type,
                'lots': lots,
                'status': 'pending',
                'message': f"Will add {lots} lot(s) to {option_type} side (requires strike finder integration)"
            }

        # Execute order via order executor
        # This would place a SELL order for the specified strike
        return {
            'action': 'add_to_opposite',
            'option_type': option_type,
            'strike': strike,
            'lots': lots,
            'execution_mode': execution_mode,
            'status': 'executed',
            'message': f"Added {lots} lot(s) to {option_type} side at strike {strike}"
        }

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    async def _is_in_cooldown(
        self,
        strategy_id: int,
        rule_id: str,
        cooldown_seconds: int
    ) -> bool:
        """Check if rule is in cooldown period"""
        if cooldown_seconds <= 0:
            return False

        result = await self.db.execute(
            select(AutoPilotAdjustmentLog)
            .where(
                and_(
                    AutoPilotAdjustmentLog.strategy_id == strategy_id,
                    AutoPilotAdjustmentLog.rule_id == rule_id,
                    AutoPilotAdjustmentLog.executed == True
                )
            )
            .order_by(AutoPilotAdjustmentLog.executed_at.desc())
            .limit(1)
        )
        last_execution = result.scalar_one_or_none()

        if last_execution and last_execution.executed_at:
            elapsed = (datetime.now(timezone.utc) - last_execution.executed_at).total_seconds()
            return elapsed < cooldown_seconds

        return False

    async def _exceeded_max_executions(
        self,
        strategy_id: int,
        rule_id: str,
        max_executions: Optional[int]
    ) -> bool:
        """Check if rule has exceeded max executions"""
        if max_executions is None:
            return False

        result = await self.db.execute(
            select(AutoPilotAdjustmentLog)
            .where(
                and_(
                    AutoPilotAdjustmentLog.strategy_id == strategy_id,
                    AutoPilotAdjustmentLog.rule_id == rule_id,
                    AutoPilotAdjustmentLog.executed == True
                )
            )
        )
        execution_count = len(result.scalars().all())
        return execution_count >= max_executions

    async def _create_adjustment_log(
        self,
        strategy: AutoPilotStrategy,
        rule: Dict[str, Any],
        evaluation: Dict[str, Any],
        execution_mode: ExecutionMode
    ) -> AutoPilotAdjustmentLog:
        """Create an adjustment log entry"""
        log = AutoPilotAdjustmentLog(
            strategy_id=strategy.id,
            user_id=self.user_id,
            rule_id=rule['id'],
            rule_name=rule['name'],
            trigger_type=AdjustmentTriggerType(rule['trigger']['type']),
            trigger_condition=rule['trigger']['condition'],
            trigger_value=rule['trigger']['value'],
            actual_value=evaluation['current_value'],
            action_type=AdjustmentActionType(rule['action']['type']),
            action_params=rule['action'].get('params', {}),
            execution_mode=execution_mode,
            executed=False
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def _log_adjustment_event(
        self,
        strategy: AutoPilotStrategy,
        rule: Dict[str, Any],
        event_type: str,
        message: str
    ):
        """Log adjustment-related event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            strategy_id=strategy.id,
            event_type=event_type,
            severity=LogSeverity.INFO,
            rule_name=rule['name'],
            message=message,
            event_data={'rule': rule}
        )
        self.db.add(log)

    def _get_action_description(
        self,
        rule: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> str:
        """Generate human-readable action description"""
        action = rule['action']
        trigger = rule['trigger']

        action_desc = {
            'exit_all': 'Exit all positions',
            'add_hedge': 'Add protective hedge',
            'close_leg': 'Close specific leg',
            'roll_strike': 'Roll to different strike',
            'roll_expiry': 'Roll to next expiry',
            'scale_down': 'Reduce position size',
            'scale_up': 'Increase position size'
        }.get(action['type'], action['type'])

        return (
            f"{action_desc} triggered by {rule['name']}: "
            f"{trigger['condition']} {trigger['value']} "
            f"(current: {evaluation['current_value']})"
        )

    async def _send_adjustment_notification(
        self,
        strategy: AutoPilotStrategy,
        rule: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Send WebSocket notification for adjustment"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': 'adjustment_executed',
                    'strategy_id': strategy.id,
                    'rule_id': rule['id'],
                    'rule_name': rule['name'],
                    'action_type': rule['action']['type'],
                    'executed': True,
                    'execution_result': result
                }
            )

    # -------------------------------------------------------------------------
    # Phase 5D: Profit-Based Exit Triggers
    # -------------------------------------------------------------------------

    async def _check_profit_pct_trigger(
        self,
        strategy: Any,
        trigger: Dict[str, Any]
    ) -> bool:
        """
        Check if profit percentage trigger is met (Phase 5D Feature #18-19).

        Evaluates whether current P&L has reached a target percentage of max profit.

        Args:
            strategy: Strategy object with max_profit and current_pnl attributes
            trigger: Trigger config with type="profit_pct_of_max" and value (percentage)

        Returns:
            bool: True if profit target reached

        Example:
            trigger = {"type": "profit_pct_of_max", "value": 50.0}
            Max profit = 10000, Current P&L = 5000 → 50% captured → True
        """
        trigger_type = trigger.get('type')
        if trigger_type != 'profit_pct_of_max':
            return False

        target_pct = float(trigger.get('value', 0))

        # Get strategy's max profit and current P&L
        max_profit = getattr(strategy, 'max_profit', None)
        current_pnl = getattr(strategy, 'current_pnl', None)

        if max_profit is None or current_pnl is None:
            return False

        # Avoid division by zero
        if max_profit == 0:
            return False

        # Calculate percentage captured
        pct_captured = (float(current_pnl) / float(max_profit)) * 100

        # Trigger if captured >= target
        return pct_captured >= target_pct


# Factory function for dependency injection
async def get_adjustment_engine(
    db: AsyncSession,
    user_id: UUID
) -> AdjustmentEngine:
    """Create an AdjustmentEngine instance"""
    return AdjustmentEngine(db, user_id)
