"""
Staged Entry Service - Phase 5I (#12, #13)

Handles half-size entry and staggered entry logic for AutoPilot strategies.

Features:
- #12 Half-Size Entry: Start with 50% position, add if market moves
- #13 Staggered Entry: Enter legs at different times based on conditions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.models.autopilot import AutoPilotStrategy, AutoPilotLeg
from backend.app.services.condition_engine import ConditionEngine
from backend.app.services.market_data import MarketDataService
from backend.app.services.order_executor import OrderExecutor
from backend.app.websocket.manager import ConnectionManager
import logging

logger = logging.getLogger(__name__)


class StagedEntryService:
    """
    Service for managing staged and staggered entry logic.

    Supports two entry patterns:
    1. Half-Size Entry: Enter partial position initially, add remaining when conditions met
    2. Staggered Entry: Enter different legs at different times based on conditions
    """

    def __init__(
        self,
        db: AsyncSession,
        market_data: MarketDataService,
        condition_engine: ConditionEngine,
        order_executor: OrderExecutor,
        websocket_manager: Optional[ConnectionManager] = None
    ):
        self.db = db
        self.market_data = market_data
        self.condition_engine = condition_engine
        self.order_executor = order_executor
        self.websocket_manager = websocket_manager

    async def check_staged_entries(self, strategy: AutoPilotStrategy) -> Dict[str, Any]:
        """
        Check if any staged entry conditions are met for a strategy.

        Called by strategy_monitor.py every 5 seconds for strategies with:
        - status = 'waiting_staged_entry'
        - staged_entry_config is not None

        Returns:
            {
                "should_execute": bool,
                "stage_number": int,
                "legs_to_enter": List[str],  # leg_ids
                "lots_multiplier": float,
                "reason": str
            }
        """
        if not strategy.staged_entry_config:
            return {"should_execute": False, "reason": "No staged entry config"}

        config = strategy.staged_entry_config
        entry_mode = config.get("mode", "half_size")  # "half_size" or "staggered"

        if entry_mode == "half_size":
            return await self._check_half_size_entry(strategy, config)
        elif entry_mode == "staggered":
            return await self._check_staggered_entry(strategy, config)
        else:
            logger.error(f"Unknown entry mode: {entry_mode}")
            return {"should_execute": False, "reason": f"Unknown mode: {entry_mode}"}

    async def _check_half_size_entry(
        self,
        strategy: AutoPilotStrategy,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check half-size entry conditions.

        Config structure:
        {
            "mode": "half_size",
            "initial_stage": {
                "legs": ["all"],  # or specific leg_ids like ["leg_1", "leg_2"]
                "lots_multiplier": 0.5
            },
            "add_stage": {
                "condition": {
                    "variable": "SPOT.CHANGE_PCT",
                    "operator": "greater_than",
                    "value": 1.0
                },
                "lots_multiplier": 0.5
            }
        }
        """
        # Check current stage from runtime_state
        runtime_state = strategy.runtime_state or {}
        current_stage = runtime_state.get("staged_entry_stage", 1)

        if current_stage == 1:
            # Initial stage already executed, check if add stage condition met
            add_config = config.get("add_stage", {})
            condition = add_config.get("condition")

            if not condition:
                return {"should_execute": False, "reason": "No add condition configured"}

            # Evaluate condition
            is_met = await self._evaluate_condition(strategy, condition)

            if is_met:
                return {
                    "should_execute": True,
                    "stage_number": 2,
                    "legs_to_enter": config.get("initial_stage", {}).get("legs", ["all"]),
                    "lots_multiplier": add_config.get("lots_multiplier", 0.5),
                    "reason": f"Add condition met: {condition.get('variable')} {condition.get('operator')} {condition.get('value')}"
                }
            else:
                return {
                    "should_execute": False,
                    "reason": "Add condition not yet met",
                    "condition_progress": await self._get_condition_progress(strategy, condition)
                }

        return {"should_execute": False, "reason": f"Stage {current_stage} already completed"}

    async def _check_staggered_entry(
        self,
        strategy: AutoPilotStrategy,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check staggered entry conditions.

        Config structure:
        {
            "mode": "staggered",
            "leg_entries": [
                {
                    "leg_ids": ["leg_1", "leg_2"],
                    "condition": {
                        "variable": "TIME.CURRENT",
                        "operator": "equals",
                        "value": "09:20"
                    },
                    "lots_multiplier": 1.0
                },
                {
                    "leg_ids": ["leg_3", "leg_4"],
                    "condition": {
                        "variable": "VIX.VALUE",
                        "operator": "less_than",
                        "value": 15.0
                    },
                    "lots_multiplier": 1.0
                }
            ]
        }
        """
        runtime_state = strategy.runtime_state or {}
        entered_leg_ids = runtime_state.get("staged_entry_entered_legs", [])

        leg_entries = config.get("leg_entries", [])

        for entry in leg_entries:
            leg_ids = entry.get("leg_ids", [])

            # Check if these legs already entered
            if any(leg_id in entered_leg_ids for leg_id in leg_ids):
                continue

            # Evaluate condition
            condition = entry.get("condition")
            if not condition:
                # No condition means immediate entry
                return {
                    "should_execute": True,
                    "stage_number": len(entered_leg_ids) + 1,
                    "legs_to_enter": leg_ids,
                    "lots_multiplier": entry.get("lots_multiplier", 1.0),
                    "reason": "Immediate entry (no condition)"
                }

            is_met = await self._evaluate_condition(strategy, condition)

            if is_met:
                return {
                    "should_execute": True,
                    "stage_number": len(entered_leg_ids) + 1,
                    "legs_to_enter": leg_ids,
                    "lots_multiplier": entry.get("lots_multiplier", 1.0),
                    "reason": f"Staggered condition met: {condition.get('variable')} {condition.get('operator')} {condition.get('value')}"
                }

        # No conditions met
        return {"should_execute": False, "reason": "No staggered entry conditions met"}

    async def _evaluate_condition(
        self,
        strategy: AutoPilotStrategy,
        condition: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition using the condition engine."""
        try:
            evaluation = await self.condition_engine.evaluate(
                conditions=[condition],
                underlying=strategy.underlying,
                legs_config=strategy.legs
            )
            return evaluation.get("is_met", False)
        except Exception as e:
            logger.error(f"Error evaluating staged entry condition: {e}")
            return False

    async def _get_condition_progress(
        self,
        strategy: AutoPilotStrategy,
        condition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get progress towards condition being met."""
        try:
            evaluation = await self.condition_engine.evaluate(
                conditions=[condition],
                underlying=strategy.underlying,
                legs_config=strategy.legs
            )
            return {
                "current_value": evaluation.get("current_value"),
                "target_value": condition.get("value"),
                "progress_pct": evaluation.get("progress_pct", 0),
                "distance": evaluation.get("distance_to_trigger")
            }
        except Exception as e:
            logger.error(f"Error getting condition progress: {e}")
            return {}

    async def execute_staged_entry(
        self,
        strategy: AutoPilotStrategy,
        stage_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a staged entry for the strategy.

        Args:
            strategy: The AutoPilot strategy
            stage_info: Result from check_staged_entries()

        Returns:
            {
                "success": bool,
                "orders_placed": List[Dict],
                "stage_completed": int,
                "error": Optional[str]
            }
        """
        try:
            legs_to_enter = stage_info.get("legs_to_enter", [])
            lots_multiplier = stage_info.get("lots_multiplier", 1.0)
            stage_number = stage_info.get("stage_number", 1)

            # Get legs to execute
            if "all" in legs_to_enter:
                # Execute all legs
                legs_config = strategy.legs
            else:
                # Execute only specified legs
                legs_config = [leg for leg in strategy.legs if leg.get("id") in legs_to_enter]

            # Apply lots multiplier
            adjusted_legs = []
            for leg in legs_config:
                adjusted_leg = leg.copy()
                adjusted_leg["quantity"] = int(leg.get("quantity", 1) * lots_multiplier)
                adjusted_legs.append(adjusted_leg)

            # Execute orders
            result = await self.order_executor.execute_basket_order(
                strategy=strategy,
                legs=adjusted_legs,
                order_type="LIMIT"  # or from strategy config
            )

            if result.get("success"):
                # Update runtime_state
                runtime_state = strategy.runtime_state or {}

                if strategy.staged_entry_config.get("mode") == "half_size":
                    runtime_state["staged_entry_stage"] = stage_number
                elif strategy.staged_entry_config.get("mode") == "staggered":
                    entered_legs = runtime_state.get("staged_entry_entered_legs", [])
                    entered_legs.extend(legs_to_enter)
                    runtime_state["staged_entry_entered_legs"] = entered_legs

                strategy.runtime_state = runtime_state

                # Check if all stages completed
                is_complete = await self._is_staged_entry_complete(strategy)

                if is_complete:
                    strategy.status = "active"
                    runtime_state["staged_entry_completed_at"] = datetime.now().isoformat()

                await self.db.commit()

                # Send WebSocket update
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_user(
                        user_id=strategy.user_id,
                        message_type="STAGED_ENTRY_EXECUTED",
                        data={
                            "strategy_id": strategy.id,
                            "stage": stage_number,
                            "legs_entered": legs_to_enter,
                            "is_complete": is_complete,
                            "reason": stage_info.get("reason")
                        }
                    )

                logger.info(
                    f"Staged entry executed for strategy {strategy.id}, "
                    f"stage {stage_number}, legs: {legs_to_enter}"
                )

                return {
                    "success": True,
                    "orders_placed": result.get("orders", []),
                    "stage_completed": stage_number,
                    "all_stages_complete": is_complete
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Order execution failed")
                }

        except Exception as e:
            logger.error(f"Error executing staged entry: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _is_staged_entry_complete(self, strategy: AutoPilotStrategy) -> bool:
        """Check if all staged entry stages are complete."""
        config = strategy.staged_entry_config
        if not config:
            return True

        mode = config.get("mode", "half_size")
        runtime_state = strategy.runtime_state or {}

        if mode == "half_size":
            # Half-size is complete after stage 2
            current_stage = runtime_state.get("staged_entry_stage", 1)
            return current_stage >= 2

        elif mode == "staggered":
            # Staggered is complete when all leg_entries are entered
            entered_legs = runtime_state.get("staged_entry_entered_legs", [])
            all_leg_ids = []
            for entry in config.get("leg_entries", []):
                all_leg_ids.extend(entry.get("leg_ids", []))

            return set(entered_legs) == set(all_leg_ids)

        return False

    async def cancel_staged_entry(self, strategy: AutoPilotStrategy) -> Dict[str, Any]:
        """
        Cancel a staged entry and revert to waiting status.

        Used when user wants to cancel a partially-entered strategy.
        """
        try:
            # Close any positions that were entered
            runtime_state = strategy.runtime_state or {}

            if runtime_state.get("staged_entry_entered_legs"):
                # Exit legs that were entered
                # This would call order_executor to close positions
                pass

            # Reset runtime state
            strategy.runtime_state = {
                "staged_entry_cancelled_at": datetime.now().isoformat(),
                "previous_state": runtime_state
            }
            strategy.status = "cancelled"

            await self.db.commit()

            logger.info(f"Staged entry cancelled for strategy {strategy.id}")

            return {"success": True}

        except Exception as e:
            logger.error(f"Error cancelling staged entry: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_staged_entry_status(self, strategy: AutoPilotStrategy) -> Dict[str, Any]:
        """
        Get current status of staged entry for display in UI.

        Returns:
            {
                "mode": "half_size" | "staggered",
                "current_stage": int,
                "total_stages": int,
                "entered_legs": List[str],
                "pending_legs": List[str],
                "next_condition": Dict,
                "progress_pct": float
            }
        """
        if not strategy.staged_entry_config:
            return {"mode": None, "progress_pct": 100}

        config = strategy.staged_entry_config
        mode = config.get("mode", "half_size")
        runtime_state = strategy.runtime_state or {}

        if mode == "half_size":
            current_stage = runtime_state.get("staged_entry_stage", 1)
            total_stages = 2

            initial_legs = config.get("initial_stage", {}).get("legs", ["all"])

            return {
                "mode": "half_size",
                "current_stage": current_stage,
                "total_stages": total_stages,
                "entered_legs": initial_legs if current_stage >= 1 else [],
                "pending_legs": [] if current_stage >= 2 else initial_legs,
                "next_condition": config.get("add_stage", {}).get("condition") if current_stage < 2 else None,
                "progress_pct": (current_stage / total_stages) * 100
            }

        elif mode == "staggered":
            entered_legs = runtime_state.get("staged_entry_entered_legs", [])
            leg_entries = config.get("leg_entries", [])
            total_legs = sum(len(entry.get("leg_ids", [])) for entry in leg_entries)

            # Find next pending entry
            next_condition = None
            for entry in leg_entries:
                leg_ids = entry.get("leg_ids", [])
                if not any(leg_id in entered_legs for leg_id in leg_ids):
                    next_condition = entry.get("condition")
                    break

            return {
                "mode": "staggered",
                "current_stage": len(entered_legs),
                "total_stages": total_legs,
                "entered_legs": entered_legs,
                "pending_legs": [
                    leg_id
                    for entry in leg_entries
                    for leg_id in entry.get("leg_ids", [])
                    if leg_id not in entered_legs
                ],
                "next_condition": next_condition,
                "progress_pct": (len(entered_legs) / total_legs * 100) if total_legs > 0 else 0
            }

        return {"mode": mode, "progress_pct": 0}
