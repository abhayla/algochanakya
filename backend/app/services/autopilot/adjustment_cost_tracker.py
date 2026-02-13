"""
Adjustment Cost Tracking Service

Tracks the cumulative cost of adjustments relative to original premium collected.
Provides insights into whether adjustments are eating into profitability.

Professional Trading Rule:
- If adjustment costs exceed 50% of original premium, consider exiting
- Track each adjustment with timestamp, type, and cost
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotOrder,
    AutoPilotLog
)


class AdjustmentCostSummary:
    """Summary of adjustment costs for a strategy"""

    def __init__(
        self,
        original_premium: Decimal,
        total_adjustment_cost: Decimal,
        adjustment_cost_pct: float,
        net_potential_profit: Decimal,
        adjustments: List[Dict],
        warning_threshold_pct: float = 50.0
    ):
        self.original_premium = original_premium
        self.total_adjustment_cost = total_adjustment_cost
        self.adjustment_cost_pct = adjustment_cost_pct
        self.net_potential_profit = net_potential_profit
        self.adjustments = adjustments
        self.warning_threshold_pct = warning_threshold_pct

        # Calculate alert level
        if adjustment_cost_pct >= 75:
            self.alert_level = "danger"
            self.alert_message = f"Adjustment costs ({adjustment_cost_pct:.1f}%) exceed 75% of original premium. Strongly consider exiting."
        elif adjustment_cost_pct >= warning_threshold_pct:
            self.alert_level = "warning"
            self.alert_message = f"Adjustment costs ({adjustment_cost_pct:.1f}%) exceed {warning_threshold_pct}% threshold."
        elif adjustment_cost_pct >= 25:
            self.alert_level = "info"
            self.alert_message = f"Adjustment costs at {adjustment_cost_pct:.1f}% of original premium."
        else:
            self.alert_level = "success"
            self.alert_message = f"Low adjustment costs ({adjustment_cost_pct:.1f}%)."

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "original_premium": float(self.original_premium),
            "total_adjustment_cost": float(self.total_adjustment_cost),
            "adjustment_cost_pct": self.adjustment_cost_pct,
            "net_potential_profit": float(self.net_potential_profit),
            "adjustments": self.adjustments,
            "warning_threshold_pct": self.warning_threshold_pct,
            "alert_level": self.alert_level,
            "alert_message": self.alert_message
        }


class AdjustmentCostTracker:
    """
    Service to track and analyze adjustment costs.

    Monitors:
    - Total cost of all adjustments
    - Cost as percentage of original premium
    - Individual adjustment history
    - Alert when costs exceed thresholds
    """

    # Adjustment action types that incur costs
    COST_INCURRING_ACTIONS = {
        "roll_strike",
        "roll_expiry",
        "add_hedge",
        "shift_leg",
        "add_to_opposite_side",
        "widen_spread",
        "convert_strategy"
    }

    # Actions that don't incur additional cost (exits)
    EXIT_ACTIONS = {
        "close_leg",
        "exit_all",
        "scale_down"
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(
        self,
        strategy: AutoPilotStrategy,
        warning_threshold_pct: float = 50.0
    ) -> AdjustmentCostSummary:
        """
        Get comprehensive adjustment cost summary for a strategy.

        Args:
            strategy: The AutoPilot strategy
            warning_threshold_pct: Percentage threshold for warning (default 50%)

        Returns:
            AdjustmentCostSummary with all cost analytics
        """
        # Get original premium collected (entry premium)
        original_premium = strategy.entry_premium or Decimal("0")

        if original_premium == 0:
            # If no entry premium, can't calculate percentages
            return AdjustmentCostSummary(
                original_premium=Decimal("0"),
                total_adjustment_cost=Decimal("0"),
                adjustment_cost_pct=0.0,
                net_potential_profit=Decimal("0"),
                adjustments=[],
                warning_threshold_pct=warning_threshold_pct
            )

        # Get all adjustment orders
        adjustment_orders = await self._get_adjustment_orders(strategy.id)

        # Calculate total adjustment cost
        total_cost = Decimal("0")
        adjustments_list = []

        for order in adjustment_orders:
            cost = self._calculate_order_cost(order)
            total_cost += cost

            adjustments_list.append({
                "timestamp": order.created_at.isoformat(),
                "order_id": order.id,
                "action_type": order.action_type,
                "cost": float(cost),
                "reason": order.notes or "Adjustment",
                "status": order.status
            })

        # Calculate metrics
        adjustment_cost_pct = float((total_cost / original_premium) * 100)
        net_potential_profit = original_premium - total_cost

        return AdjustmentCostSummary(
            original_premium=original_premium,
            total_adjustment_cost=total_cost,
            adjustment_cost_pct=adjustment_cost_pct,
            net_potential_profit=net_potential_profit,
            adjustments=adjustments_list,
            warning_threshold_pct=warning_threshold_pct
        )

    async def _get_adjustment_orders(self, strategy_id: int) -> List[AutoPilotOrder]:
        """Get all adjustment-related orders for a strategy"""
        query = select(AutoPilotOrder).where(
            and_(
                AutoPilotOrder.strategy_id == strategy_id,
                AutoPilotOrder.order_type == "adjustment",
                AutoPilotOrder.status.in_(["completed", "executed"])
            )
        ).order_by(AutoPilotOrder.created_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    def _calculate_order_cost(self, order: AutoPilotOrder) -> Decimal:
        """
        Calculate the cost of an adjustment order.

        For credit adjustments (selling premium), cost is negative (we receive)
        For debit adjustments (buying protection), cost is positive (we pay)
        """
        # Get order details
        filled_qty = order.filled_quantity or 0
        avg_price = order.average_price or Decimal("0")

        if filled_qty == 0 or avg_price == 0:
            return Decimal("0")

        # Determine if this was a debit or credit
        # For now, assume positive average_price means we paid (debit)
        # Negative average_price means we received (credit)

        # Cost = quantity × price × lot_size
        # For simplicity, assume lot_size is already factored into average_price
        cost = Decimal(str(filled_qty)) * avg_price

        # If the action type is a hedge or roll, it's typically a cost
        if order.action_type in ["add_hedge", "roll_strike", "roll_expiry"]:
            return abs(cost)  # Always positive cost

        # If closing/exiting, it might be a credit (receiving premium back)
        if order.action_type in self.EXIT_ACTIONS:
            # Exit costs are what we pay to close
            return abs(cost)

        return abs(cost)

    async def check_cost_threshold(
        self,
        strategy: AutoPilotStrategy,
        threshold_pct: float = 50.0
    ) -> Dict:
        """
        Check if adjustment costs exceed threshold.

        Returns:
            Dictionary with threshold check results
        """
        summary = await self.get_summary(strategy, threshold_pct)

        exceeded = summary.adjustment_cost_pct >= threshold_pct

        return {
            "threshold_exceeded": exceeded,
            "current_pct": summary.adjustment_cost_pct,
            "threshold_pct": threshold_pct,
            "alert_level": summary.alert_level,
            "alert_message": summary.alert_message,
            "recommendation": self._get_recommendation(summary)
        }

    def _get_recommendation(self, summary: AdjustmentCostSummary) -> str:
        """Generate recommendation based on adjustment cost analysis"""
        pct = summary.adjustment_cost_pct

        if pct >= 75:
            return "Exit position immediately. Adjustment costs are consuming profitability."
        elif pct >= 60:
            return "Consider exiting. Further adjustments will likely result in net loss."
        elif pct >= 50:
            return "Adjustment costs are high. Avoid further adjustments unless absolutely necessary."
        elif pct >= 35:
            return "Monitor closely. One more adjustment may push costs over 50%."
        elif pct >= 20:
            return "Adjustment costs are moderate. Continue monitoring."
        else:
            return "Adjustment costs are low. Position is still profitable after adjustments."

    async def log_adjustment_cost_alert(
        self,
        strategy: AutoPilotStrategy,
        summary: AdjustmentCostSummary
    ):
        """Log an alert to AutoPilotLog when costs exceed threshold"""
        if summary.alert_level in ["warning", "danger"]:
            log = AutoPilotLog(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                event_type="adjustment_cost_alert",
                severity=summary.alert_level,
                message=summary.alert_message,
                details={
                    "adjustment_cost_pct": summary.adjustment_cost_pct,
                    "total_adjustment_cost": float(summary.total_adjustment_cost),
                    "original_premium": float(summary.original_premium),
                    "net_potential_profit": float(summary.net_potential_profit),
                    "adjustment_count": len(summary.adjustments)
                }
            )
            self.db.add(log)
            await self.db.commit()

    async def track_new_adjustment(
        self,
        strategy: AutoPilotStrategy,
        action_type: str,
        estimated_cost: Decimal,
        notes: str = None
    ) -> Dict:
        """
        Track a new adjustment before execution.

        Returns projected cost impact if this adjustment is executed.
        """
        current_summary = await self.get_summary(strategy)

        # Calculate projected totals
        projected_cost = current_summary.total_adjustment_cost + estimated_cost
        projected_pct = float((projected_cost / current_summary.original_premium) * 100) if current_summary.original_premium > 0 else 0
        projected_profit = current_summary.original_premium - projected_cost

        return {
            "current_cost": float(current_summary.total_adjustment_cost),
            "current_pct": current_summary.adjustment_cost_pct,
            "estimated_new_cost": float(estimated_cost),
            "projected_total_cost": float(projected_cost),
            "projected_cost_pct": projected_pct,
            "projected_profit": float(projected_profit),
            "recommendation": "proceed" if projected_pct < 50 else "reconsider" if projected_pct < 75 else "do_not_adjust"
        }
