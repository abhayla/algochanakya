"""
Adjustment Engine Service - Phase 3 + Phase 5D

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

Action Types:
- add_hedge: Add protective leg
- close_leg: Close specific leg
- roll_strike: Move strike closer/farther from ATM
- roll_expiry: Move to next expiry
- exit_all: Exit entire position
- scale_down: Reduce position size by X%
- scale_up: Increase position size by X%
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

logger = logging.getLogger(__name__)


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


# Factory function for dependency injection
async def get_adjustment_engine(
    db: AsyncSession,
    user_id: UUID
) -> AdjustmentEngine:
    """Create an AdjustmentEngine instance"""
    return AdjustmentEngine(db, user_id)
