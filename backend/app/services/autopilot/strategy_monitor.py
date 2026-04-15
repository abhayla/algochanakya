"""
Strategy Monitor

Background service that monitors active strategies.
Evaluates conditions and triggers order execution.
Uses broker abstraction layer for broker-agnostic operation.

Phase 3 Integrations:
- Kill Switch: Check if enabled before processing strategies
- Adjustment Engine: Evaluate and execute adjustment rules
- Confirmation Service: Handle semi-auto execution mode
- Trailing Stop: Update and check trailing stop levels
- Auto-Exit: Intraday auto-exit at configured time
- Greeks: Calculate and store Greeks snapshot

Phase 5 Integrations:
- Delta Tracking: Monitor net delta per leg and strategy
- Delta Alerts: Send alerts when delta thresholds crossed
- Position Legs: Update Greeks for individual position legs

AI Week 3 Integrations:
- AI Config Limits: Check VIX, daily lots, max strategies per day
- Confidence Threshold: Enforce minimum confidence to trade
- Paper/Live Mode: Enforce mode and check graduation status
- Position Sizing: Integrated via OrderExecutor (uses AI config tiers)
"""
import asyncio
from datetime import datetime, time, date, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from contextlib import asynccontextmanager
from decimal import Decimal
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from kiteconnect import KiteConnect

from app.database import AsyncSessionLocal
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotUserSettings, AutoPilotLog,
    AutoPilotConditionEval, ExecutionMode
)
from app.services.legacy.market_data import MarketDataService, get_market_data_service
from app.services.autopilot.condition_engine import ConditionEngine, get_condition_engine
from app.services.autopilot.order_executor import OrderExecutor, get_order_executor
from app.services.autopilot.kill_switch import KillSwitchService
from app.services.autopilot.adjustment_engine import AdjustmentEngine
from app.services.autopilot.confirmation_service import ConfirmationService
from app.services.autopilot.trailing_stop import TrailingStopService
from app.services.options.greeks_calculator import GreeksCalculatorService
from app.services.autopilot.position_leg_service import PositionLegService
from app.services.options.iv_metrics_service import get_iv_metrics_service
from app.services.autopilot.delta_band_service import get_delta_band_service
from app.services.ai.config_service import AIConfigService
from app.services.brokers.base import BrokerAdapter
from app.websocket.manager import get_ws_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_session():
    """Context manager for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class StrategyMonitor:
    """
    Monitors active AutoPilot strategies.

    Responsibilities:
    - Poll for waiting/active strategies
    - Evaluate entry conditions
    - Trigger order execution when conditions met
    - Update strategy status
    - Send WebSocket updates
    - Check kill switch status (Phase 3)
    - Evaluate adjustment rules (Phase 3)
    - Handle semi-auto confirmations (Phase 3)
    - Update trailing stops (Phase 3)
    - Auto-exit at configured time (Phase 3)
    - Calculate Greeks snapshots (Phase 3)
    - Track delta per leg and strategy (Phase 5)
    - Send delta threshold alerts (Phase 5)
    """

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    POLL_INTERVAL = 5  # seconds

    def __init__(
        self,
        broker_adapter: Union[BrokerAdapter, KiteConnect],
        market_data: MarketDataService,
        condition_engine: ConditionEngine
    ):
        # Support both BrokerAdapter (preferred) and KiteConnect (legacy)
        if isinstance(broker_adapter, BrokerAdapter):
            self.broker_adapter = broker_adapter
            self.kite = broker_adapter.get_kite_client()  # For services requiring KiteConnect
        else:
            # Legacy KiteConnect passed directly
            self.kite = broker_adapter
            self.broker_adapter = broker_adapter  # Will be treated as KiteConnect in order_executor

        self.market_data = market_data
        self.condition_engine = condition_engine
        self.order_executor = get_order_executor(broker_adapter, market_data)
        self.ws_manager = get_ws_manager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_market_status: Optional[bool] = None

        # Phase 3 services
        self.kill_switch = KillSwitchService()
        self.adjustment_engine = AdjustmentEngine(market_data)
        self.confirmation_service = ConfirmationService()
        self.trailing_stop = TrailingStopService(market_data)
        self.greeks_calculator = GreeksCalculatorService()

        # Phase 5 services (initialized per-session in methods that need db)
        self.position_leg_service = None

        # AI integration — injected externally when AI module is active
        self.ai_monitor = None

    async def start(self):
        """Start the monitor background task."""
        if self._running:
            logger.warning("Strategy monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Strategy monitor started")

    async def stop(self):
        """Stop the monitor background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Strategy monitor stopped")

    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now()
        current_time = now.time()
        # Also check for weekday (Mon=0, Fri=4)
        weekday = now.weekday()
        if weekday > 4:  # Weekend
            return False
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                market_open = self.is_market_open()

                # Broadcast market status if changed
                if self._last_market_status != market_open:
                    self._last_market_status = market_open
                    await self.ws_manager.send_market_status(
                        is_open=market_open,
                        message="Market is open" if market_open else "Market is closed"
                    )

                if market_open:
                    await self._process_strategies()
                else:
                    logger.debug("Market closed, skipping monitoring")

                await asyncio.sleep(self.POLL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.POLL_INTERVAL)

    async def _process_strategies(self):
        """Process all active strategies."""
        async with get_db_session() as db:
            # Phase 3: Check global kill switch first
            kill_switch_status = await self.kill_switch.get_status(db)
            if kill_switch_status.is_enabled:
                logger.warning(f"Kill switch is ENABLED: {kill_switch_status.reason}. Skipping strategy processing.")
                # Broadcast kill switch status to all connected clients
                await self.ws_manager.send_system_alert(
                    alert_type="kill_switch_active",
                    message=f"Kill Switch Active: {kill_switch_status.reason}",
                    data={"triggered_at": kill_switch_status.triggered_at.isoformat() if kill_switch_status.triggered_at else None}
                )
                return

            # Get all waiting, active, waiting_staged_entry, and reentry_waiting strategies
            result = await db.execute(
                select(AutoPilotStrategy).where(
                    AutoPilotStrategy.status.in_(["waiting", "active", "waiting_staged_entry", "reentry_waiting"])
                )
            )
            strategies = result.scalars().all()

            for strategy in strategies:
                try:
                    await self._process_strategy(db, strategy)
                except Exception as e:
                    logger.error(f"Error processing strategy {strategy.id}: {e}")

    async def _process_ai_strategies(
        self,
        db: AsyncSession,
        strategies: list,
        ai_config
    ):
        """
        Process AI-managed strategies via AIMonitor.

        Filters strategies to only AI-managed ones, then delegates to
        ai_monitor.process_ai_strategies(). Errors are caught to protect
        the main monitoring loop.
        """
        if not self.ai_monitor:
            return

        # Filter to AI-managed strategies only
        ai_strategies = [s for s in strategies if getattr(s, 'ai_managed', False)]
        if not ai_strategies or not ai_config or not getattr(ai_config, 'ai_enabled', False):
            return

        try:
            user_id = str(ai_strategies[0].user_id)
            await self.ai_monitor.process_ai_strategies(
                user_id=user_id,
                user_config=ai_config,
                active_strategies=ai_strategies
            )
        except Exception as e:
            logger.error(f"AI monitor error (non-fatal): {e}")

    async def _process_strategy(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Process a single strategy."""

        # Check schedule
        if not self._is_schedule_active(strategy):
            return

        # Check user risk limits
        risk_ok, risk_message = await self._check_risk_limits(db, strategy)
        if not risk_ok:
            logger.warning(f"Risk limits exceeded for strategy {strategy.id}: {risk_message}")
            await self.ws_manager.send_risk_alert(
                user_id=str(strategy.user_id),
                alert_type="risk_limit",
                message=risk_message,
                data={"strategy_id": strategy.id}
            )
            return

        # AI Week 3: Check AI config limits for AI-deployed strategies
        ai_limits_ok, ai_limit_message = await self._check_ai_limits(db, strategy)
        if not ai_limits_ok:
            logger.warning(f"AI limits exceeded for strategy {strategy.id}: {ai_limit_message}")
            await self.ws_manager.send_risk_alert(
                user_id=str(strategy.user_id),
                alert_type="ai_limit",
                message=f"AI Limit: {ai_limit_message}",
                data={"strategy_id": strategy.id, "ai_deployed": True}
            )
            return

        if strategy.status == "waiting":
            # Evaluate entry conditions
            await self._evaluate_and_execute(db, strategy)

        elif strategy.status == "waiting_staged_entry":
            # Phase 5I: Check staged entry conditions
            await self._check_staged_entry(db, strategy)

        elif strategy.status == "reentry_waiting":
            # Phase 3: Check re-entry conditions
            await self._check_reentry(db, strategy)

        elif strategy.status == "active":
            # Update P&L
            await self._update_pnl(db, strategy)

            # Phase 3: Check intraday auto-exit time
            if await self._check_auto_exit_time(db, strategy):
                return  # Strategy was exited

            # Phase 3: Update trailing stop levels
            await self._update_trailing_stop(db, strategy)

            # Check risk-based exits (includes trailing stop check)
            await self._check_risk_exits(db, strategy)

            # Phase 3: Evaluate adjustment rules
            await self._evaluate_adjustments(db, strategy)

            # Phase 3: Calculate and store Greeks snapshot
            await self._update_greeks(db, strategy)

            # Phase 5B: Update Phase 5B monitoring metrics
            await self._update_phase5b_tracking(db, strategy)

            # Phase 5C: Update Phase 5C entry enhancement metrics
            await self._update_phase5c_tracking(db, strategy)

            # Phase 5: Update delta tracking and check thresholds
            await self._update_delta_tracking(db, strategy)

    async def _evaluate_and_execute(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Evaluate conditions and execute if met."""

        # Prepare Greeks snapshot (Phase 5A + 5B + 5C)
        runtime_state = strategy.runtime_state or {}
        greeks_snapshot = {
            # Phase 5A: Greeks
            'delta': float(strategy.net_delta or 0.0),
            'gamma': float(strategy.net_gamma or 0.0),
            'theta': float(strategy.net_theta or 0.0),
            'vega': float(strategy.net_vega or 0.0),

            # Phase 5B #51: Theta tracking
            'theta_tracking': runtime_state.get('theta_tracking', {}),

            # Phase 5B #50: Premium decay
            'entry_premium': runtime_state.get('entry_premium', 0.0),
            'current_value': runtime_state.get('current_value', 0.0),

            # Phase 5B #53: IV metrics
            'iv_rank': runtime_state.get('iv_rank', 0.0),
            'iv_percentile': runtime_state.get('iv_percentile', 0.0),

            # Phase 5B #52: Breakevens (from payoff calculator if available)
            'breakevens': runtime_state.get('breakevens', {}),

            # Phase 5C #6-8: OI metrics
            'oi_pcr': runtime_state.get('oi_pcr', 0.0),
            'oi_max_pain': runtime_state.get('oi_max_pain', 0.0),
            'oi_change': runtime_state.get('oi_change', 0.0),

            # Phase 5C #11: Probability OTM
            'probability_otm': runtime_state.get('probability_otm', 0.0),

            # Phase 5C #14, #24: Days tracking
            'dte': runtime_state.get('dte', 0),
            'days_in_trade': runtime_state.get('days_in_trade', 0),
            'entry_time': runtime_state.get('entry_time'),
        }

        # Evaluate conditions
        eval_result = await self.condition_engine.evaluate(
            strategy_id=strategy.id,
            entry_conditions=strategy.entry_conditions or {},
            underlying=strategy.underlying,
            legs_config=strategy.legs_config or [],
            greeks_snapshot=greeks_snapshot
        )

        # Store condition evaluation results
        await self._store_condition_eval(db, strategy.id, eval_result)

        # Prepare condition states for WebSocket
        condition_states = [
            {
                "condition_id": r.condition_id,
                "variable": r.variable,
                "operator": r.operator,
                "current_value": r.current_value,
                "target_value": r.target_value,
                "is_met": r.is_met,
                "progress_pct": r.progress_pct,
                "distance_to_trigger": r.distance_to_trigger
            }
            for r in eval_result.individual_results
        ]

        # Send condition update via WebSocket
        await self.ws_manager.send_condition_update(
            user_id=str(strategy.user_id),
            strategy_id=strategy.id,
            conditions_met=eval_result.all_conditions_met,
            condition_states=condition_states
        )

        if eval_result.all_conditions_met:
            logger.info(f"Conditions met for strategy {strategy.id}, executing entry")

            # Check if paper trading
            user_settings = await self._get_user_settings(db, strategy.user_id)
            paper_trading = (
                user_settings.paper_trading_mode if user_settings
                else (strategy.runtime_state or {}).get('paper_trading', False)
            )

            # Execute entry
            success, results = await self.order_executor.execute_entry(
                db=db,
                strategy=strategy,
                dry_run=paper_trading
            )

            if success:
                # Update status to active
                old_status = strategy.status
                strategy.status = "active"
                strategy.activated_at = datetime.now()

                # Update runtime state with positions
                runtime_state = strategy.runtime_state or {}
                runtime_state['entry_time'] = datetime.now().isoformat()
                runtime_state['paper_trading'] = paper_trading
                runtime_state['entry_results'] = [
                    {"order_id": r.order_id, "success": r.success, "leg_id": r.leg_id}
                    for r in results
                ]

                # Build current_positions from order results
                current_positions = []
                for i, (result, leg) in enumerate(zip(results, strategy.legs_config or [])):
                    if result.success:
                        current_positions.append({
                            "leg_id": leg.get('id', f'leg_{i}'),
                            "leg_index": i,
                            "tradingsymbol": leg.get('tradingsymbol', ''),
                            "quantity": strategy.lots * self._get_lot_size(strategy.underlying) * leg.get('quantity_multiplier', 1),
                            "transaction_type": leg.get('transaction_type'),
                            "contract_type": leg.get('contract_type'),
                            "entry_price": float(result.executed_price) if result.executed_price else 0,
                            "exchange": "NFO",
                            "product": "NRML" if strategy.position_type == "positional" else "MIS"
                        })
                        # Adjust quantity sign for SELL positions
                        if leg.get('transaction_type') == 'SELL':
                            current_positions[-1]['quantity'] = -abs(current_positions[-1]['quantity'])

                runtime_state['current_positions'] = current_positions
                strategy.runtime_state = runtime_state

                await db.commit()

                # Log entry
                log = AutoPilotLog(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    event_type="entry_executed",
                    severity="info",
                    message=f"Strategy entry executed successfully{' (paper trading)' if paper_trading else ''}",
                    event_data={"results": [{"order_id": r.order_id, "success": r.success} for r in results]}
                )
                db.add(log)
                await db.commit()

                # Send status change notification
                await self.ws_manager.send_status_change(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    old_status=old_status,
                    new_status="active",
                    reason="Entry conditions met"
                )

                # Send order notifications
                for result in results:
                    if result.success:
                        await self.ws_manager.send_order_update(
                            user_id=str(strategy.user_id),
                            strategy_id=strategy.id,
                            order_id=int(result.order_id) if result.order_id else 0,
                            event_type=__import__('app.websocket.manager', fromlist=['MessageType']).MessageType.ORDER_PLACED,
                            order_data={
                                "kite_order_id": result.kite_order_id,
                                "leg_id": result.leg_id,
                                "message": result.message
                            }
                        )
            else:
                # Handle execution failure
                old_status = strategy.status
                strategy.status = "error"
                runtime_state = strategy.runtime_state or {}
                runtime_state['error'] = "Entry execution failed"
                runtime_state['error_time'] = datetime.now().isoformat()
                runtime_state['failed_results'] = [
                    {"leg_id": r.leg_id, "error": r.error}
                    for r in results if not r.success
                ]
                strategy.runtime_state = runtime_state
                await db.commit()

                # Log error
                log = AutoPilotLog(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    event_type="entry_failed",
                    severity="error",
                    message="Strategy entry execution failed",
                    event_data={"results": [{"leg_id": r.leg_id, "error": r.error} for r in results]}
                )
                db.add(log)
                await db.commit()

                await self.ws_manager.send_status_change(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    old_status=old_status,
                    new_status="error",
                    reason="Entry execution failed"
                )

    async def _check_staged_entry(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """
        Phase 5I: Check if staged entry conditions are met for next stage.

        Called when strategy status is 'waiting_staged_entry'.
        Evaluates whether to execute the next stage of entry (half-size add or staggered leg).
        """
        try:
            # Import staged entry service
            from backend.app.services.staged_entry_service import StagedEntryService

            # Initialize staged entry service
            staged_service = StagedEntryService(
                db=db,
                market_data=self.market_data,
                condition_engine=self.condition_engine,
                order_executor=self.order_executor,
                websocket_manager=self.ws_manager
            )

            # Check if any staged entry conditions are met
            stage_info = await staged_service.check_staged_entries(strategy)

            if not stage_info.get("should_execute"):
                # Conditions not met yet, send progress update
                progress_data = await staged_service.get_staged_entry_status(strategy)
                await self.ws_manager.broadcast_to_user(
                    user_id=strategy.user_id,
                    message_type="STAGED_ENTRY_PROGRESS",
                    data={
                        "strategy_id": strategy.id,
                        "status": progress_data,
                        "reason": stage_info.get("reason", "Waiting for conditions")
                    }
                )
                return

            # Conditions met, execute the next stage
            logger.info(
                f"Staged entry conditions met for strategy {strategy.id}: "
                f"{stage_info.get('reason')}"
            )

            # Log the staged entry trigger
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="staged_entry_triggered",
                severity="info",
                message=f"Staged entry stage {stage_info.get('stage_number')} triggered",
                event_data=stage_info
            )
            db.add(log)
            await db.commit()

            # Execute the staged entry
            result = await staged_service.execute_staged_entry(strategy, stage_info)

            if result.get("success"):
                logger.info(
                    f"Staged entry executed successfully for strategy {strategy.id}, "
                    f"stage {result.get('stage_completed')}"
                )

                # Log successful execution
                log = AutoPilotLog(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    event_type="staged_entry_executed",
                    severity="info",
                    message=f"Staged entry stage {result.get('stage_completed')} executed",
                    event_data={
                        "stage": result.get('stage_completed'),
                        "orders": result.get('orders_placed', []),
                        "all_complete": result.get('all_stages_complete', False)
                    }
                )
                db.add(log)
                await db.commit()

                # Send WebSocket notification (already sent by staged_service)
                # Status already updated to 'active' if all stages complete

            else:
                # Execution failed
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Staged entry execution failed for strategy {strategy.id}: {error_msg}")

                # Log failure
                log = AutoPilotLog(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    event_type="staged_entry_failed",
                    severity="error",
                    message=f"Staged entry execution failed: {error_msg}",
                    event_data={"error": error_msg}
                )
                db.add(log)

                # Update strategy status to error
                strategy.status = "error"
                await db.commit()

                # Send WebSocket notification
                await self.ws_manager.broadcast_to_user(
                    user_id=strategy.user_id,
                    message_type="STRATEGY_ERROR",
                    data={
                        "strategy_id": strategy.id,
                        "error": error_msg,
                        "reason": "Staged entry execution failed"
                    }
                )

        except Exception as e:
            logger.error(f"Error in _check_staged_entry for strategy {strategy.id}: {e}", exc_info=True)
            # Don't crash the monitor, just log and continue

    async def _update_pnl(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Update P&L for active strategy."""
        runtime_state = strategy.runtime_state or {}
        current_positions = runtime_state.get('current_positions', [])

        if not current_positions:
            return

        # Get current LTPs
        instruments = [f"NFO:{p['tradingsymbol']}" for p in current_positions if p.get('tradingsymbol')]
        if not instruments:
            return

        try:
            ltp_data = await self.market_data.get_ltp(instruments)
        except Exception as e:
            logger.warning(f"Could not get LTP for P&L update: {e}")
            return

        total_pnl = 0
        for position in current_positions:
            tradingsymbol = position.get('tradingsymbol')
            if not tradingsymbol:
                continue

            key = f"NFO:{tradingsymbol}"
            current_ltp = float(ltp_data.get(key, 0))
            entry_price = float(position.get('entry_price', 0))
            quantity = position.get('quantity', 0)

            # Calculate P&L (positive qty = long, negative = short)
            pnl = (current_ltp - entry_price) * quantity
            total_pnl += pnl

            # Update position with current LTP
            position['current_ltp'] = current_ltp
            position['unrealized_pnl'] = pnl

        # Update runtime state
        runtime_state['current_pnl'] = total_pnl
        runtime_state['pnl_updated_at'] = datetime.now().isoformat()
        runtime_state['current_positions'] = current_positions
        strategy.runtime_state = runtime_state
        await db.commit()

        # Send P&L update
        await self.ws_manager.send_pnl_update(
            user_id=str(strategy.user_id),
            strategy_id=strategy.id,
            realized_pnl=runtime_state.get('realized_pnl', 0),
            unrealized_pnl=total_pnl,
            total_pnl=runtime_state.get('realized_pnl', 0) + total_pnl
        )

    async def _check_risk_exits(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Check if risk limits trigger exit."""
        risk_settings = strategy.risk_settings or {}
        runtime_state = strategy.runtime_state or {}
        current_pnl = runtime_state.get('current_pnl', 0)

        should_exit = False
        exit_reason = ""

        # Check max loss
        max_loss = risk_settings.get('max_loss')
        if max_loss and current_pnl <= -float(max_loss):
            should_exit = True
            exit_reason = f"Max loss limit ({max_loss}) reached"

        # Check max profit (target)
        max_profit = risk_settings.get('max_profit')
        if max_profit and current_pnl >= float(max_profit):
            should_exit = True
            exit_reason = f"Target profit ({max_profit}) reached"

        # Check trailing stop loss
        trailing_sl = risk_settings.get('trailing_stop_loss')
        if trailing_sl:
            peak_pnl = runtime_state.get('peak_pnl', 0)
            if current_pnl > peak_pnl:
                runtime_state['peak_pnl'] = current_pnl
                strategy.runtime_state = runtime_state
                await db.commit()
            elif peak_pnl > 0 and (peak_pnl - current_pnl) >= float(trailing_sl):
                should_exit = True
                exit_reason = f"Trailing stop loss ({trailing_sl}) triggered"

        # Check time stop
        time_stop = risk_settings.get('time_stop')
        if time_stop:
            current_time = datetime.now().strftime("%H:%M")
            if current_time >= time_stop:
                should_exit = True
                exit_reason = f"Time stop ({time_stop}) reached"

        if should_exit:
            logger.info(f"Risk exit triggered for strategy {strategy.id}: {exit_reason}")

            paper_trading = runtime_state.get('paper_trading', False)

            success, results = await self.order_executor.execute_exit(
                db=db,
                strategy=strategy,
                exit_type="market",
                reason=exit_reason,
                dry_run=paper_trading
            )

            # Update status
            old_status = strategy.status
            strategy.status = "completed"
            strategy.completed_at = datetime.now()
            runtime_state['exit_reason'] = exit_reason
            runtime_state['exit_time'] = datetime.now().isoformat()
            runtime_state['realized_pnl'] = runtime_state.get('realized_pnl', 0) + current_pnl
            strategy.runtime_state = runtime_state
            await db.commit()

            # Log exit
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="exit_executed",
                severity="info",
                message=f"Strategy exit executed: {exit_reason}",
                event_data={"reason": exit_reason, "pnl": current_pnl}
            )
            db.add(log)
            await db.commit()

            await self.ws_manager.send_status_change(
                user_id=str(strategy.user_id),
                strategy_id=strategy.id,
                old_status=old_status,
                new_status="completed",
                reason=exit_reason
            )

    async def _check_risk_limits(self, db: AsyncSession, strategy: AutoPilotStrategy) -> tuple[bool, str]:
        """Check if user's risk limits allow execution."""
        user_settings = await self._get_user_settings(db, strategy.user_id)

        if not user_settings:
            return True, ""  # No limits set

        # Check max active strategies
        if user_settings.max_active_strategies:
            active_count = await db.execute(
                select(AutoPilotStrategy).where(
                    AutoPilotStrategy.user_id == strategy.user_id,
                    AutoPilotStrategy.status.in_(["waiting", "active"]),
                    AutoPilotStrategy.id != strategy.id
                )
            )
            active_strategies = active_count.scalars().all()
            if len(active_strategies) >= user_settings.max_active_strategies:
                return False, f"Max active strategies ({user_settings.max_active_strategies}) limit reached"

        # Check no trade first/last minutes
        now = datetime.now()
        minutes_since_open = (now - datetime.combine(now.date(), self.MARKET_OPEN)).total_seconds() / 60
        minutes_to_close = (datetime.combine(now.date(), self.MARKET_CLOSE) - now).total_seconds() / 60

        if minutes_since_open < user_settings.no_trade_first_minutes:
            return False, f"No trading in first {user_settings.no_trade_first_minutes} minutes"

        if minutes_to_close < user_settings.no_trade_last_minutes:
            return False, f"No trading in last {user_settings.no_trade_last_minutes} minutes"

        # TODO: Check daily loss limit
        # TODO: Check cooldown after loss

        return True, ""

    async def _check_ai_limits(self, db: AsyncSession, strategy: AutoPilotStrategy) -> tuple[bool, str]:
        """
        AI Week 3: Check if AI config limits allow execution.

        Checks:
        - AI enabled
        - VIX limit
        - Daily lots limit
        - Max strategies per day
        - Min confidence threshold
        - Paper/Live mode and graduation status
        """
        # Only check AI limits for AI-deployed strategies
        if not strategy.ai_deployed:
            return True, ""

        # Get AI config
        ai_config = await AIConfigService.get_or_create_config(strategy.user_id, db)

        if not ai_config:
            return True, ""  # No AI config set

        # Check if AI is enabled
        if not ai_config.ai_enabled:
            return False, "AI trading is disabled in AI Settings"

        # Check VIX limit
        if ai_config.max_vix_to_trade:
            try:
                vix_data = await self.market_data.get_vix()
                current_vix = float(vix_data.ltp)

                if current_vix > float(ai_config.max_vix_to_trade):
                    return False, f"VIX {current_vix:.2f} exceeds max limit {ai_config.max_vix_to_trade}"
            except Exception as e:
                logger.warning(f"Failed to check VIX limit: {e}")

        # Check confidence threshold
        if ai_config.min_confidence_to_trade and strategy.ai_confidence_score:
            if float(strategy.ai_confidence_score) < float(ai_config.min_confidence_to_trade):
                return False, f"Confidence {strategy.ai_confidence_score}% below minimum {ai_config.min_confidence_to_trade}%"

        # Check max strategies per day limit
        if ai_config.max_strategies_per_day:
            from sqlalchemy import func, and_

            today = date.today()
            deployed_today = await db.execute(
                select(func.count(AutoPilotStrategy.id)).where(
                    and_(
                        AutoPilotStrategy.user_id == strategy.user_id,
                        AutoPilotStrategy.ai_deployed == True,
                        func.date(AutoPilotStrategy.activated_at) == today,
                        AutoPilotStrategy.id != strategy.id  # Exclude current strategy
                    )
                )
            )
            count_today = deployed_today.scalar() or 0

            if count_today >= ai_config.max_strategies_per_day:
                return False, f"Max AI strategies per day ({ai_config.max_strategies_per_day}) limit reached"

        # Check max lots per day limit
        if ai_config.max_lots_per_day:
            from sqlalchemy import func, and_

            today = date.today()
            lots_used_today = await db.execute(
                select(func.sum(AutoPilotStrategy.lots)).where(
                    and_(
                        AutoPilotStrategy.user_id == strategy.user_id,
                        AutoPilotStrategy.ai_deployed == True,
                        AutoPilotStrategy.status.in_(["waiting", "active"]),
                        func.date(AutoPilotStrategy.activated_at) == today,
                        AutoPilotStrategy.id != strategy.id  # Exclude current strategy
                    )
                )
            )
            total_lots_today = lots_used_today.scalar() or 0

            if total_lots_today + strategy.lots > ai_config.max_lots_per_day:
                return False, f"Daily lots limit exceeded: {total_lots_today + strategy.lots}/{ai_config.max_lots_per_day}"

        # Check paper/live mode and graduation status
        if ai_config.autonomy_mode == "live":
            # Verify strategy is also in live mode
            if strategy.trading_mode != "live":
                return False, "Strategy must be in live mode when AI is configured for live trading"

            # Check graduation status
            can_graduate = await AIConfigService.can_graduate_to_live(db, strategy.user_id)
            if not can_graduate:
                return False, "User has not graduated from paper trading yet"

        elif ai_config.autonomy_mode == "paper":
            # Force paper mode for safety
            if strategy.trading_mode != "paper":
                logger.warning(f"Strategy {strategy.id} trading_mode changed to paper (AI config requires paper mode)")
                strategy.trading_mode = "paper"
                await db.commit()

        return True, ""

    async def _get_user_settings(self, db: AsyncSession, user_id) -> Optional[AutoPilotUserSettings]:
        """Get user settings."""
        result = await db.execute(
            select(AutoPilotUserSettings).where(
                AutoPilotUserSettings.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def _store_condition_eval(self, db: AsyncSession, strategy_id: int, eval_result):
        """Store condition evaluation results."""
        # Delete old evaluations for this strategy
        from sqlalchemy import delete
        await db.execute(
            delete(AutoPilotConditionEval).where(
                AutoPilotConditionEval.strategy_id == strategy_id
            )
        )

        # Insert new evaluations
        for i, result in enumerate(eval_result.individual_results):
            eval_record = AutoPilotConditionEval(
                strategy_id=strategy_id,
                condition_type="entry",
                condition_index=i,
                variable=result.variable,
                operator=result.operator,
                target_value=result.target_value,
                current_value=result.current_value,
                is_satisfied=result.is_met,
                progress_pct=result.progress_pct,
                distance_to_trigger=result.distance_to_trigger
            )
            db.add(eval_record)

        await db.commit()

    def _is_schedule_active(self, strategy: AutoPilotStrategy) -> bool:
        """Check if strategy schedule allows execution."""
        schedule = strategy.schedule_config or {}

        # Check active days
        active_days = schedule.get('active_days', ['MON', 'TUE', 'WED', 'THU', 'FRI'])
        current_day = datetime.now().strftime("%a").upper()[:3]
        if current_day not in active_days:
            return False

        # Check time window
        start_time = schedule.get('start_time', '09:15')
        end_time = schedule.get('end_time', '15:30')
        current_time = datetime.now().strftime("%H:%M")

        if not (start_time <= current_time <= end_time):
            return False

        # Check if specific dates are set
        start_date = schedule.get('start_date')
        end_date = schedule.get('end_date')
        today = date.today()

        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                if today < start:
                    return False
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                if today > end:
                    return False
            except ValueError:
                pass

        return True

    def _get_lot_size(self, underlying: str) -> int:
        """Get lot size for underlying."""
        from app.constants import get_lot_size
        return get_lot_size(underlying)

    # =========================================================================
    # Phase 3: Auto-Exit, Trailing Stop, Adjustments, Greeks
    # =========================================================================

    async def _check_auto_exit_time(self, db: AsyncSession, strategy: AutoPilotStrategy) -> bool:
        """
        Check if intraday auto-exit time has been reached.
        Returns True if strategy was exited.
        """
        # Get user settings for auto-exit time
        user_settings = await self._get_user_settings(db, strategy.user_id)
        if not user_settings or not user_settings.auto_exit_time:
            return False

        # Only for MIS/intraday positions
        if strategy.position_type != "intraday":
            return False

        current_time = datetime.now().strftime("%H:%M")
        auto_exit_time = user_settings.auto_exit_time

        if current_time >= auto_exit_time:
            logger.info(f"Auto-exit time ({auto_exit_time}) reached for strategy {strategy.id}")

            runtime_state = strategy.runtime_state or {}
            current_pnl = runtime_state.get('current_pnl', 0)
            paper_trading = runtime_state.get('paper_trading', False)

            # Execute exit
            success, results = await self.order_executor.execute_exit(
                db=db,
                strategy=strategy,
                exit_type="market",
                reason=f"Intraday auto-exit at {auto_exit_time}",
                dry_run=paper_trading
            )

            # Update status
            old_status = strategy.status
            strategy.status = "completed"
            strategy.completed_at = datetime.now()
            runtime_state['exit_reason'] = f"Intraday auto-exit at {auto_exit_time}"
            runtime_state['exit_time'] = datetime.now().isoformat()
            runtime_state['realized_pnl'] = runtime_state.get('realized_pnl', 0) + current_pnl
            strategy.runtime_state = runtime_state
            await db.commit()

            # Log exit
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="auto_exit",
                severity="info",
                message=f"Strategy auto-exited at {auto_exit_time}",
                event_data={"reason": "intraday_auto_exit", "pnl": current_pnl}
            )
            db.add(log)
            await db.commit()

            # Send WebSocket update
            await self.ws_manager.send_status_change(
                user_id=str(strategy.user_id),
                strategy_id=strategy.id,
                old_status=old_status,
                new_status="completed",
                reason=f"Intraday auto-exit at {auto_exit_time}"
            )

            return True

        return False

    async def _update_trailing_stop(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Update trailing stop levels using the TrailingStopService."""
        try:
            runtime_state = strategy.runtime_state or {}
            current_pnl = runtime_state.get('current_pnl', 0)

            # Get current spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if spot_price is None:
                return

            # Update trailing stop via service
            trailing_status = await self.trailing_stop.update_trailing_stop(
                db=db,
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                current_pnl=current_pnl,
                spot_price=spot_price,
                risk_settings=strategy.risk_settings or {}
            )

            if trailing_status:
                # Store updated trailing stop info in runtime state
                runtime_state['trailing_stop'] = {
                    'peak_pnl': trailing_status.peak_pnl,
                    'current_stop_level': trailing_status.current_stop_level,
                    'distance_to_stop': trailing_status.distance_to_stop,
                    'is_active': trailing_status.is_active,
                    'updated_at': datetime.now().isoformat()
                }
                strategy.runtime_state = runtime_state
                await db.commit()

                # Send trailing stop update via WebSocket
                await self.ws_manager.send_strategy_update(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    update_type="trailing_stop",
                    data={
                        "peak_pnl": trailing_status.peak_pnl,
                        "current_stop_level": trailing_status.current_stop_level,
                        "distance_to_stop": trailing_status.distance_to_stop,
                        "is_active": trailing_status.is_active
                    }
                )

        except Exception as e:
            logger.error(f"Error updating trailing stop for strategy {strategy.id}: {e}")

    async def _evaluate_adjustments(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Evaluate adjustment rules and execute if triggered."""
        try:
            adjustment_rules = strategy.adjustment_rules or []
            if not adjustment_rules:
                return

            runtime_state = strategy.runtime_state or {}
            current_pnl = runtime_state.get('current_pnl', 0)
            current_positions = runtime_state.get('current_positions', [])

            # Get current market data
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            vix = await self.market_data.get_vix()

            # Evaluate adjustments
            triggered_adjustment = await self.adjustment_engine.evaluate_adjustments(
                strategy_id=strategy.id,
                adjustment_rules=adjustment_rules,
                current_pnl=current_pnl,
                spot_price=spot_price,
                current_positions=current_positions,
                vix=vix
            )

            if triggered_adjustment:
                logger.info(f"Adjustment triggered for strategy {strategy.id}: {triggered_adjustment.action}")

                # Check execution mode
                execution_mode = strategy.execution_mode
                paper_trading = runtime_state.get('paper_trading', False)

                if execution_mode == ExecutionMode.SEMI_AUTO:
                    # Create confirmation request instead of executing
                    confirmation = await self.confirmation_service.create_confirmation(
                        db=db,
                        user_id=strategy.user_id,
                        strategy_id=strategy.id,
                        action_type="adjustment",
                        action_description=triggered_adjustment.description,
                        action_data={
                            "rule_id": triggered_adjustment.rule_id,
                            "action": triggered_adjustment.action,
                            "legs_to_modify": triggered_adjustment.legs_to_modify
                        }
                    )

                    # Send notification
                    await self.ws_manager.send_confirmation_request(
                        user_id=str(strategy.user_id),
                        strategy_id=strategy.id,
                        confirmation_id=confirmation.id,
                        action_type="adjustment",
                        description=triggered_adjustment.description,
                        expires_at=confirmation.expires_at
                    )

                    # Log pending confirmation
                    log = AutoPilotLog(
                        user_id=strategy.user_id,
                        strategy_id=strategy.id,
                        event_type="adjustment_pending",
                        severity="warning",
                        message=f"Adjustment pending confirmation: {triggered_adjustment.description}",
                        event_data={"rule_id": triggered_adjustment.rule_id, "confirmation_id": confirmation.id}
                    )
                    db.add(log)
                    await db.commit()

                else:
                    # Execute adjustment immediately (full auto mode)
                    success = await self.adjustment_engine.execute_adjustment(
                        db=db,
                        strategy=strategy,
                        adjustment=triggered_adjustment,
                        order_executor=self.order_executor,
                        dry_run=paper_trading
                    )

                    if success:
                        # Log successful adjustment
                        log = AutoPilotLog(
                            user_id=strategy.user_id,
                            strategy_id=strategy.id,
                            event_type="adjustment_executed",
                            severity="info",
                            message=f"Adjustment executed: {triggered_adjustment.description}",
                            event_data={"rule_id": triggered_adjustment.rule_id, "action": triggered_adjustment.action}
                        )
                        db.add(log)
                        await db.commit()

                        # Send WebSocket update
                        await self.ws_manager.send_strategy_update(
                            user_id=str(strategy.user_id),
                            strategy_id=strategy.id,
                            update_type="adjustment_executed",
                            data={
                                "rule_id": triggered_adjustment.rule_id,
                                "action": triggered_adjustment.action,
                                "description": triggered_adjustment.description
                            }
                        )

        except Exception as e:
            logger.error(f"Error evaluating adjustments for strategy {strategy.id}: {e}")

    async def _update_greeks(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Calculate and store Greeks snapshot for the strategy."""
        try:
            runtime_state = strategy.runtime_state or {}
            current_positions = runtime_state.get('current_positions', [])

            if not current_positions:
                return

            # Get current spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if spot_price is None:
                return

            # Convert positions to legs format for Greeks calculator
            legs = []
            for pos in current_positions:
                legs.append({
                    "strike": pos.get('strike', 0),
                    "contract_type": pos.get('contract_type', 'CE'),
                    "expiry": pos.get('expiry'),
                    "quantity": pos.get('quantity', 0),
                    "premium": pos.get('current_ltp', 0),
                    "iv": pos.get('iv')  # Optional, will be calculated if not provided
                })

            # Calculate Greeks
            greeks_snapshot = self.greeks_calculator.calculate_greeks_snapshot(
                legs=legs,
                spot_price=spot_price,
                current_time=datetime.now()
            )

            # Store Greeks in runtime state
            runtime_state['greeks'] = {
                'net_delta': greeks_snapshot.net_delta,
                'net_gamma': greeks_snapshot.net_gamma,
                'net_theta': greeks_snapshot.net_theta,
                'net_vega': greeks_snapshot.net_vega,
                'net_rho': greeks_snapshot.net_rho,
                'delta_exposure': greeks_snapshot.delta_exposure,
                'leg_greeks': [
                    {
                        'strike': lg.strike,
                        'contract_type': lg.contract_type,
                        'delta': lg.delta,
                        'gamma': lg.gamma,
                        'theta': lg.theta,
                        'vega': lg.vega,
                        'rho': lg.rho
                    }
                    for lg in greeks_snapshot.leg_greeks
                ],
                'updated_at': datetime.now().isoformat()
            }
            strategy.runtime_state = runtime_state
            await db.commit()

            # Send Greeks update via WebSocket (throttled - every 30 seconds)
            last_greeks_update = runtime_state.get('last_greeks_ws_update')
            now = datetime.now()
            should_send = (
                last_greeks_update is None or
                (now - datetime.fromisoformat(last_greeks_update)).total_seconds() >= 30
            )

            if should_send:
                runtime_state['last_greeks_ws_update'] = now.isoformat()
                strategy.runtime_state = runtime_state
                await db.commit()

                await self.ws_manager.send_strategy_update(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    update_type="greeks",
                    data={
                        "net_delta": greeks_snapshot.net_delta,
                        "net_gamma": greeks_snapshot.net_gamma,
                        "net_theta": greeks_snapshot.net_theta,
                        "net_vega": greeks_snapshot.net_vega,
                        "delta_exposure": greeks_snapshot.delta_exposure
                    }
                )

        except Exception as e:
            logger.error(f"Error calculating Greeks for strategy {strategy.id}: {e}")

    async def _update_phase5b_tracking(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """
        Update Phase 5B monitoring metrics.
        Tracks: Theta burn rate, premium decay, IV rank, delta bands.
        Phase 5B Features #48-53.
        """
        try:
            runtime_state = strategy.runtime_state or {}

            # Get current spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if not spot_price:
                return

            # Phase 5B #51: Track Theta Burn Rate
            current_theta = float(strategy.net_theta or 0.0)
            dte = strategy.dte or 1
            entry_premium = float(strategy.entry_premium or 0.0)

            # Expected daily theta decay = total premium / days to expiry
            expected_daily_theta = entry_premium / dte if dte > 0 and entry_premium > 0 else 0

            theta_tracking = {
                'current_theta': current_theta,
                'expected_daily': expected_daily_theta,
                'actual_vs_expected_pct': (current_theta / expected_daily_theta * 100) if expected_daily_theta != 0 else 0
            }
            runtime_state['theta_tracking'] = theta_tracking

            # Phase 5B #50: Track Premium Decay
            current_positions = runtime_state.get('current_positions', [])
            current_value = 0.0
            for pos in current_positions:
                current_ltp = float(pos.get('current_ltp', 0))
                quantity = int(pos.get('quantity', 0))
                current_value += current_ltp * abs(quantity)

            runtime_state['current_value'] = current_value
            runtime_state['entry_premium'] = entry_premium

            # Phase 5B #53: IV Rank and Percentile
            try:
                iv_metrics_service = get_iv_metrics_service(self.market_data)
                iv_metrics = await iv_metrics_service.get_iv_metrics(strategy.underlying)
                runtime_state['iv_rank'] = iv_metrics.get('iv_rank', 0.0)
                runtime_state['iv_percentile'] = iv_metrics.get('iv_percentile', 0.0)
            except Exception as e:
                logger.warning(f"Could not fetch IV metrics for strategy {strategy.id}: {e}")
                runtime_state['iv_rank'] = 0.0
                runtime_state['iv_percentile'] = 0.0

            # Phase 5B #49: Delta Band Monitoring
            net_delta = float(strategy.net_delta or 0.0)
            try:
                delta_band_service = get_delta_band_service(self.market_data)

                # Get leg Greeks from runtime state
                greeks_data = runtime_state.get('greeks', {})
                leg_greeks = greeks_data.get('leg_greeks', [])

                # Check delta band
                delta_band_status = await delta_band_service.check_delta_band(
                    strategy_id=strategy.id,
                    net_delta=net_delta,
                    band_threshold=delta_band_service.get_delta_band_config(strategy.adjustment_rules or {}),
                    leg_greeks=leg_greeks
                )

                runtime_state['delta_band'] = {
                    'out_of_band': delta_band_status.out_of_band,
                    'severity': delta_band_status.severity,
                    'suggested_action': delta_band_status.suggested_action,
                    'alternative_action': delta_band_status.alternative_action
                }

                # Send alert if out of band
                if delta_band_status.out_of_band and delta_band_status.severity == 'critical':
                    await self.ws_manager.send_system_alert(
                        alert_type="delta_band_breach",
                        message=f"Strategy {strategy.id}: Delta out of band ({net_delta:+.3f})",
                        data={
                            "strategy_id": strategy.id,
                            "net_delta": net_delta,
                            "threshold": delta_band_status.band_threshold,
                            "suggested_action": delta_band_status.suggested_action
                        }
                    )

            except Exception as e:
                logger.warning(f"Could not check delta bands for strategy {strategy.id}: {e}")

            strategy.runtime_state = runtime_state
            await db.commit()

        except Exception as e:
            logger.error(f"Error updating Phase 5B tracking for strategy {strategy.id}: {e}")

    async def _update_phase5c_tracking(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """
        Update Phase 5C entry enhancement metrics.
        Tracks: OI metrics, Probability OTM, DTE, Days in Trade.
        Phase 5C Features #6-11, #14, #24.
        """
        try:
            runtime_state = strategy.runtime_state or {}

            # Phase 5C #14: DTE (Days to Expiry)
            # Calculate from legs config
            dte = 0
            if strategy.legs_config:
                for leg in strategy.legs_config:
                    expiry = leg.get('expiry')
                    if expiry:
                        try:
                            from datetime import date, datetime
                            if isinstance(expiry, str):
                                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                            elif isinstance(expiry, date):
                                expiry_date = expiry
                            else:
                                continue

                            today = date.today()
                            dte = max(dte, (expiry_date - today).days)
                        except Exception as e:
                            logger.debug(f"Error calculating DTE: {e}")
                            continue

            runtime_state['dte'] = max(0, dte)

            # Phase 5C #24: Days in Trade
            if strategy.status == 'active' and strategy.entry_time:
                try:
                    from datetime import datetime
                    if isinstance(strategy.entry_time, str):
                        entry_dt = datetime.fromisoformat(strategy.entry_time.replace('Z', '+00:00'))
                    else:
                        entry_dt = strategy.entry_time

                    now = datetime.now(entry_dt.tzinfo) if entry_dt.tzinfo else datetime.now()
                    days_in_trade = (now - entry_dt).days
                    runtime_state['days_in_trade'] = max(0, days_in_trade)
                    runtime_state['entry_time'] = strategy.entry_time
                except Exception as e:
                    logger.debug(f"Error calculating days in trade: {e}")
                    runtime_state['days_in_trade'] = 0
            else:
                runtime_state['days_in_trade'] = 0

            # Phase 5C #6-8: OI Metrics (PCR, Max Pain, OI Change)
            try:
                from app.services.options.oi_analysis_service import OIAnalysisService

                oi_service = OIAnalysisService(self.kite, db)

                # Get expiry from legs
                expiry_str = None
                if strategy.legs_config and len(strategy.legs_config) > 0:
                    first_leg_expiry = strategy.legs_config[0].get('expiry')
                    if first_leg_expiry:
                        if isinstance(first_leg_expiry, str):
                            expiry_str = first_leg_expiry
                        elif isinstance(first_leg_expiry, date):
                            expiry_str = first_leg_expiry.strftime("%Y-%m-%d")

                if expiry_str:
                    # Get PCR
                    pcr = await oi_service.get_pcr(strategy.underlying, expiry_str)
                    runtime_state['oi_pcr'] = pcr

                    # Get Max Pain
                    max_pain = await oi_service.get_max_pain(strategy.underlying, expiry_str)
                    runtime_state['oi_max_pain'] = max_pain

                    # Get ATM OI Change
                    oi_change = await oi_service.get_atm_oi_change(strategy.underlying, expiry_str)
                    runtime_state['oi_change'] = oi_change

                    logger.debug(
                        f"Phase 5C OI Metrics for strategy {strategy.id}: "
                        f"PCR={pcr:.2f}, Max Pain={max_pain}, OI Change={oi_change:.1f}%"
                    )
                else:
                    runtime_state['oi_pcr'] = 0.0
                    runtime_state['oi_max_pain'] = 0.0
                    runtime_state['oi_change'] = 0.0

            except Exception as e:
                logger.warning(f"Could not fetch OI metrics for strategy {strategy.id}: {e}")
                runtime_state['oi_pcr'] = 0.0
                runtime_state['oi_max_pain'] = 0.0
                runtime_state['oi_change'] = 0.0

            # Phase 5C #11: Probability OTM
            try:
                from app.services.options.greeks_calculator import GreeksCalculatorService

                greeks_calc = GreeksCalculatorService(db, strategy.user_id)

                # Get spot price
                spot_data = await self.market_data.get_spot_price(strategy.underlying)
                spot_price = float(spot_data.ltp)

                min_prob_otm = 100.0  # Start with 100% (most conservative)

                # Calculate probability OTM for each leg
                if strategy.legs_config:
                    for leg in strategy.legs_config:
                        strike = float(leg.get('strike', 0))
                        option_type = leg.get('option_type', 'CE').upper()
                        iv = float(leg.get('iv', 0.20))  # Default 20% IV
                        expiry = leg.get('expiry')

                        if strike and expiry:
                            # Calculate time to expiry
                            try:
                                from datetime import date, datetime
                                if isinstance(expiry, str):
                                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                                elif isinstance(expiry, date):
                                    expiry_date = expiry
                                else:
                                    continue

                                today = date.today()
                                days_to_expiry = (expiry_date - today).days
                                time_to_expiry = max(0, days_to_expiry / 365.0)

                                if time_to_expiry > 0:
                                    is_call = option_type in ('CE', 'CALL', 'C')

                                    prob_otm = greeks_calc.calculate_probability_otm(
                                        spot=spot_price,
                                        strike=strike,
                                        time_to_expiry=time_to_expiry,
                                        volatility=iv,
                                        is_call=is_call
                                    )

                                    # Track minimum (most conservative)
                                    min_prob_otm = min(min_prob_otm, prob_otm)

                                    # Also store per-leg
                                    leg_id = leg.get('id') or leg.get('leg_id')
                                    if leg_id:
                                        runtime_state[f'probability_otm_{leg_id}'] = prob_otm

                            except Exception as e:
                                logger.debug(f"Error calculating probability OTM for leg: {e}")
                                continue

                runtime_state['probability_otm'] = min_prob_otm if min_prob_otm < 100.0 else 0.0

                logger.debug(
                    f"Phase 5C Probability OTM for strategy {strategy.id}: "
                    f"Min={min_prob_otm:.1f}%"
                )

            except Exception as e:
                logger.warning(f"Could not calculate probability OTM for strategy {strategy.id}: {e}")
                runtime_state['probability_otm'] = 0.0

            strategy.runtime_state = runtime_state
            await db.commit()

        except Exception as e:
            logger.error(f"Error updating Phase 5C tracking for strategy {strategy.id}: {e}")

    async def _update_delta_tracking(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """
        Update delta tracking for position legs and check thresholds.
        Phase 5 feature.
        """
        try:
            # Initialize position leg service if needed
            if not self.position_leg_service:
                self.position_leg_service = PositionLegService(self.kite, db)

            # Get all open position legs for this strategy
            from app.models.autopilot import AutoPilotPositionLeg, PositionLegStatus
            result = await db.execute(
                select(AutoPilotPositionLeg).where(
                    AutoPilotPositionLeg.strategy_id == strategy.id,
                    AutoPilotPositionLeg.status == PositionLegStatus.OPEN.value
                )
            )
            position_legs = result.scalars().all()

            if not position_legs:
                return

            # Get spot price
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            if not spot_price:
                return

            # Update Greeks for each leg
            net_delta = Decimal('0')
            net_theta = Decimal('0')
            net_gamma = Decimal('0')
            net_vega = Decimal('0')

            for leg in position_legs:
                if not leg.tradingsymbol:
                    continue

                # Get current price
                try:
                    ltp_data = await self.market_data.get_ltp([f"NFO:{leg.tradingsymbol}"])
                    current_ltp = ltp_data.get(f"NFO:{leg.tradingsymbol}")

                    if current_ltp:
                        # Update leg Greeks
                        updated_leg = await self.position_leg_service.update_leg_greeks(
                            strategy_id=strategy.id,
                            leg_id=leg.leg_id,
                            spot_price=Decimal(str(spot_price)),
                            current_price=Decimal(str(current_ltp))
                        )

                        # Accumulate net Greeks
                        if updated_leg.delta:
                            net_delta += updated_leg.delta
                        if updated_leg.theta:
                            net_theta += updated_leg.theta
                        if updated_leg.gamma:
                            net_gamma += updated_leg.gamma
                        if updated_leg.vega:
                            net_vega += updated_leg.vega

                except Exception as e:
                    logger.warning(f"Error updating Greeks for leg {leg.leg_id}: {e}")

            # Update strategy net Greeks (Phase 5 columns)
            strategy.net_delta = net_delta
            strategy.net_theta = net_theta
            strategy.net_gamma = net_gamma
            strategy.net_vega = net_vega
            await db.commit()

            # Check delta thresholds and send alerts
            await self._check_delta_thresholds(db, strategy, net_delta)

        except Exception as e:
            logger.error(f"Error updating delta tracking for strategy {strategy.id}: {e}")

    async def _check_delta_thresholds(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        net_delta: Decimal
    ):
        """
        Check if delta has crossed any thresholds and send alerts.
        Phase 5 feature.
        """
        try:
            # Get user settings for delta thresholds
            user_settings = await self._get_user_settings(db, strategy.user_id)
            if not user_settings or not user_settings.delta_alert_enabled:
                return

            abs_delta = abs(float(net_delta))

            # Determine alert level
            alert_level = None
            alert_message = None

            danger_threshold = user_settings.delta_danger_threshold or 0.50
            warning_threshold = user_settings.delta_warning_threshold or 0.30
            watch_threshold = user_settings.delta_watch_threshold or 0.15

            if abs_delta >= danger_threshold:
                alert_level = "danger"
                alert_message = f"DANGER: Net delta ({abs_delta:.2f}) exceeded danger threshold ({danger_threshold})"
            elif abs_delta >= warning_threshold:
                alert_level = "warning"
                alert_message = f"WARNING: Net delta ({abs_delta:.2f}) exceeded warning threshold ({warning_threshold})"
            elif abs_delta >= watch_threshold:
                alert_level = "watch"
                alert_message = f"WATCH: Net delta ({abs_delta:.2f}) exceeded watch threshold ({watch_threshold})"

            if alert_level:
                # Check if we already sent this alert recently (throttle)
                runtime_state = strategy.runtime_state or {}
                last_delta_alert = runtime_state.get('last_delta_alert', {})
                last_alert_level = last_delta_alert.get('level')
                last_alert_time = last_delta_alert.get('time')

                # Only send if level changed or > 5 minutes since last alert
                should_send = (
                    last_alert_level != alert_level or
                    not last_alert_time or
                    (datetime.now() - datetime.fromisoformat(last_alert_time)).total_seconds() > 300
                )

                if should_send:
                    # Update runtime state
                    runtime_state['last_delta_alert'] = {
                        'level': alert_level,
                        'time': datetime.now().isoformat(),
                        'delta': float(net_delta)
                    }
                    strategy.runtime_state = runtime_state
                    await db.commit()

                    # Log the alert
                    log = AutoPilotLog(
                        user_id=strategy.user_id,
                        strategy_id=strategy.id,
                        event_type="delta_alert",
                        severity="warning" if alert_level in ["warning", "danger"] else "info",
                        message=alert_message,
                        event_data={
                            "net_delta": float(net_delta),
                            "alert_level": alert_level,
                            "threshold": danger_threshold if alert_level == "danger"
                                        else warning_threshold if alert_level == "warning"
                                        else watch_threshold
                        }
                    )
                    db.add(log)
                    await db.commit()

                    # Send WebSocket alert
                    await self.ws_manager.send_risk_alert(
                        user_id=str(strategy.user_id),
                        alert_type="delta_threshold",
                        message=alert_message,
                        data={
                            "strategy_id": strategy.id,
                            "net_delta": float(net_delta),
                            "alert_level": alert_level,
                            "net_theta": float(strategy.net_theta) if strategy.net_theta else None,
                            "net_gamma": float(strategy.net_gamma) if strategy.net_gamma else None,
                            "net_vega": float(strategy.net_vega) if strategy.net_vega else None
                        }
                    )

        except Exception as e:
            logger.error(f"Error checking delta thresholds for strategy {strategy.id}: {e}")

    async def _check_reentry(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """
        Check if exited strategy should re-enter.

        Phase 3: Re-Entry Logic
        - Check if re-entry is enabled
        - Check cooldown period
        - Check max re-entries limit
        - Evaluate re-entry conditions
        - Execute re-entry if all checks pass
        """
        try:
            reentry_config = strategy.reentry_config or {}

            # Check if re-entry is enabled
            if not reentry_config.get('enabled', False):
                logger.debug(f"Re-entry disabled for strategy {strategy.id}")
                return

            # Check max re-entries limit
            max_reentries = reentry_config.get('max_reentries', 1)
            reentry_count = reentry_config.get('reentry_count', 0)

            if reentry_count >= max_reentries:
                logger.info(f"Strategy {strategy.id} reached max re-entries ({max_reentries})")
                # Mark as completed since no more re-entries allowed
                strategy.status = "completed"
                strategy.completed_at = datetime.now(timezone.utc)

                # Log completion
                log = AutoPilotLog(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    event_type="reentry_limit_reached",
                    severity="info",
                    message=f"Strategy completed: Max re-entries ({max_reentries}) reached",
                    event_data={
                        "reentry_count": reentry_count,
                        "max_reentries": max_reentries
                    }
                )
                db.add(log)
                await db.commit()

                # Send WebSocket update
                await self.ws_manager.send_strategy_update(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    status="completed",
                    message="Strategy completed: Max re-entries reached"
                )
                return

            # Check cooldown period
            cooldown_minutes = reentry_config.get('cooldown_minutes', 15)
            if strategy.completed_at:
                time_since_exit = datetime.now(timezone.utc) - strategy.completed_at
                cooldown_seconds = cooldown_minutes * 60

                if time_since_exit.total_seconds() < cooldown_seconds:
                    remaining_seconds = cooldown_seconds - time_since_exit.total_seconds()
                    logger.debug(
                        f"Strategy {strategy.id} in cooldown period: "
                        f"{remaining_seconds:.0f}s remaining"
                    )
                    return

            # Evaluate re-entry conditions
            reentry_conditions = reentry_config.get('conditions', {})

            if not reentry_conditions or not reentry_conditions.get('conditions'):
                logger.warning(f"No re-entry conditions defined for strategy {strategy.id}")
                return

            # Evaluate conditions using condition engine
            eval_result = await self.condition_engine.evaluate(
                strategy_id=strategy.id,
                entry_conditions=reentry_conditions,
                underlying=strategy.underlying,
                legs_config=strategy.legs_config
            )

            # Save condition evaluation
            condition_eval = AutoPilotConditionEval(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                underlying=strategy.underlying,
                all_conditions_met=eval_result.all_conditions_met,
                condition_results=eval_result.condition_results,
                spot_price=eval_result.market_context.get('spot_price'),
                vix_value=eval_result.market_context.get('vix'),
                iv_rank=eval_result.market_context.get('iv_rank')
            )
            db.add(condition_eval)
            await db.commit()

            # Send WebSocket update with condition status
            await self.ws_manager.send_condition_evaluated(
                user_id=str(strategy.user_id),
                strategy_id=strategy.id,
                all_conditions_met=eval_result.all_conditions_met,
                condition_results=eval_result.condition_results,
                market_context=eval_result.market_context
            )

            if not eval_result.all_conditions_met:
                logger.debug(f"Re-entry conditions not met for strategy {strategy.id}")
                return

            # All checks passed - execute re-entry
            logger.info(f"Re-entry conditions met for strategy {strategy.id}, executing re-entry")

            # Increment re-entry count
            reentry_config['reentry_count'] = reentry_count + 1
            strategy.reentry_config = reentry_config

            # Change status back to waiting (will be processed in next cycle)
            strategy.status = "waiting"
            strategy.completed_at = None

            # Log re-entry
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="reentry_triggered",
                severity="info",
                message=f"Re-entry triggered (attempt {reentry_count + 1}/{max_reentries})",
                event_data={
                    "reentry_count": reentry_count + 1,
                    "max_reentries": max_reentries,
                    "condition_results": eval_result.condition_results
                }
            )
            db.add(log)
            await db.commit()

            # Send WebSocket update
            await self.ws_manager.send_strategy_update(
                user_id=str(strategy.user_id),
                strategy_id=strategy.id,
                status="waiting",
                message=f"Re-entry triggered (attempt {reentry_count + 1}/{max_reentries})",
                data={
                    "reentry_count": reentry_count + 1,
                    "max_reentries": max_reentries
                }
            )

        except Exception as e:
            logger.error(f"Error checking re-entry for strategy {strategy.id}: {e}")


# Singleton instance
_strategy_monitor: Optional[StrategyMonitor] = None


async def get_strategy_monitor(
    broker_adapter: Union[BrokerAdapter, KiteConnect]
) -> StrategyMonitor:
    """
    Get or create StrategyMonitor instance.

    Args:
        broker_adapter: BrokerAdapter instance (preferred) or KiteConnect (legacy)

    Returns:
        StrategyMonitor singleton instance
    """
    global _strategy_monitor
    if _strategy_monitor is None:
        # Get kite for market data service (still requires KiteConnect internally)
        if isinstance(broker_adapter, BrokerAdapter):
            kite = broker_adapter.get_kite_client()
        else:
            kite = broker_adapter

        market_data = get_market_data_service(kite)
        condition_engine = get_condition_engine(market_data)
        _strategy_monitor = StrategyMonitor(broker_adapter, market_data, condition_engine)
    return _strategy_monitor


async def stop_strategy_monitor():
    """Stop and cleanup the strategy monitor."""
    global _strategy_monitor
    if _strategy_monitor:
        await _strategy_monitor.stop()
        _strategy_monitor = None
