"""
Autonomy Status Service (Priority 3.1)

Tracks user's autonomy level progression through the Trust Ladder:
- Level 1: Sandbox (Paper trading mode)
- Level 2: Supervised (Live trading with semi-auto execution)
- Level 3: Autonomous (Live trading with full auto execution)

Provides status tracking, graduation progress, and degradation detection.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIUserConfig
from app.models.ai_risk_state import AIRiskState, RiskState

logger = logging.getLogger(__name__)


class AutonomyLevel(str, Enum):
    """
    Autonomy Trust Ladder levels.

    Users progress: SANDBOX -> SUPERVISED -> AUTONOMOUS
    """
    SANDBOX = "sandbox"        # Paper trading - Level 1
    SUPERVISED = "supervised"  # Live + Semi-auto - Level 2
    AUTONOMOUS = "autonomous"  # Live + Auto - Level 3


class DegradationReason(str, Enum):
    """Reasons for autonomy degradation or pause."""
    HIGH_DRAWDOWN = "high_drawdown"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    LOW_WIN_RATE = "low_win_rate"
    RISK_STATE_PAUSED = "risk_state_paused"
    MANUAL_PAUSE = "manual_pause"
    WEEKLY_LOSS_LIMIT = "weekly_loss_limit"


# Graduation thresholds (same as existing paper graduation)
GRADUATION_THRESHOLDS = {
    "min_trades": 25,
    "min_win_rate": 55.0,  # Percentage
    "min_pnl": Decimal("0.00"),  # Must be positive
    "min_days_trading": 7,  # Optional: minimum days of experience
}

# Degradation thresholds
DEGRADATION_THRESHOLDS = {
    "max_drawdown": Decimal("20.00"),  # Pause above 20% drawdown
    "max_consecutive_losses": 5,
    "min_win_rate_maintenance": 45.0,  # Below this triggers warning
}


class AutonomyStatusService:
    """
    Service for tracking autonomy level progression and degradation.

    The Trust Ladder helps build user confidence through graduated autonomy:
    1. Sandbox - Safe learning environment with paper trades
    2. Supervised - Live trading with AI confirmation prompts
    3. Autonomous - Full AI control without confirmations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_autonomy_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive autonomy status for a user.

        Args:
            user_id: User's UUID

        Returns:
            Dict containing:
            - current_level: Current autonomy level
            - level_details: Details about current level
            - progress: Progress toward next level
            - unlock_criteria: Requirements for next level
            - warnings: Any degradation warnings
            - is_paused: Whether autonomy is paused
            - pause_reason: Reason for pause (if paused)
        """
        # Get user's AI config
        config = await self._get_user_config(user_id)
        if not config:
            return self._get_default_status()

        # Determine current level
        current_level = self._determine_level(config)

        # Get progress toward next level
        progress = await self._calculate_progress(config, current_level)

        # Get unlock criteria for next level
        unlock_criteria = self._get_unlock_criteria(current_level, config)

        # Check for degradation/warnings
        warnings, is_paused, pause_reason = await self._check_degradation(user_id, config)

        return {
            "current_level": current_level.value,
            "level_index": self._get_level_index(current_level),
            "level_details": self._get_level_details(current_level),
            "progress": progress,
            "unlock_criteria": unlock_criteria,
            "warnings": warnings,
            "is_paused": is_paused,
            "pause_reason": pause_reason,
            "ai_enabled": config.ai_enabled,
            "graduation_approved": config.paper_graduation_approved,
            "stats": {
                "trades_completed": config.paper_trades_completed,
                "win_rate": float(config.paper_win_rate),
                "total_pnl": float(config.paper_total_pnl),
                "days_trading": self._calculate_days_trading(config.paper_start_date),
                "current_drawdown": float(config.current_drawdown_pct),
            }
        }

    async def _get_user_config(self, user_id: UUID) -> Optional[AIUserConfig]:
        """Get user's AI configuration."""
        result = await self.db.execute(
            select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _determine_level(self, config: AIUserConfig) -> AutonomyLevel:
        """
        Determine user's current autonomy level based on config.

        Logic:
        - Paper mode -> SANDBOX
        - Live mode + not graduated -> SANDBOX (shouldn't happen but safety)
        - Live mode + graduated + semi_auto -> SUPERVISED
        - Live mode + graduated + auto -> AUTONOMOUS
        """
        # Paper mode = Sandbox
        if config.autonomy_mode == 'paper':
            return AutonomyLevel.SANDBOX

        # Live mode but not graduated = still Sandbox (shouldn't happen)
        if not config.paper_graduation_approved:
            return AutonomyLevel.SANDBOX

        # Live mode + graduated = check execution preferences
        # For now, if they're in live mode, they're at least Supervised
        # Full autonomous requires explicit opt-in (which we can track later)
        # Default: Live mode = Supervised unless they've reached full autonomy

        # Check if they've met all criteria for full autonomy
        if self._meets_autonomous_criteria(config):
            return AutonomyLevel.AUTONOMOUS

        return AutonomyLevel.SUPERVISED

    def _meets_autonomous_criteria(self, config: AIUserConfig) -> bool:
        """
        Check if user meets criteria for full autonomous mode.

        For now, using same thresholds as graduation but could be stricter.
        """
        return (
            config.paper_graduation_approved and
            config.autonomy_mode == 'live' and
            config.paper_trades_completed >= GRADUATION_THRESHOLDS["min_trades"] * 2 and  # 50 trades for full auto
            float(config.paper_win_rate) >= GRADUATION_THRESHOLDS["min_win_rate"] and
            config.paper_total_pnl >= GRADUATION_THRESHOLDS["min_pnl"]
        )

    def _get_level_index(self, level: AutonomyLevel) -> int:
        """Get numeric index for level (0-2)."""
        return {
            AutonomyLevel.SANDBOX: 0,
            AutonomyLevel.SUPERVISED: 1,
            AutonomyLevel.AUTONOMOUS: 2,
        }.get(level, 0)

    def _get_level_details(self, level: AutonomyLevel) -> Dict[str, Any]:
        """Get details about a specific level."""
        details = {
            AutonomyLevel.SANDBOX: {
                "name": "Sandbox",
                "description": "Paper trading mode - practice without real money",
                "icon": "flask",
                "color": "blue",
                "features": [
                    "Simulated trades",
                    "Learn AI behavior",
                    "Zero financial risk",
                    "Track paper P&L"
                ]
            },
            AutonomyLevel.SUPERVISED: {
                "name": "Supervised",
                "description": "Live trading with AI confirmation prompts",
                "icon": "user-check",
                "color": "yellow",
                "features": [
                    "Real trades",
                    "AI recommendations",
                    "Confirmation required",
                    "Safety guardrails"
                ]
            },
            AutonomyLevel.AUTONOMOUS: {
                "name": "Autonomous",
                "description": "Full AI control - trades execute automatically",
                "icon": "robot",
                "color": "green",
                "features": [
                    "Auto execution",
                    "No confirmations",
                    "ML-powered decisions",
                    "24/7 monitoring"
                ]
            },
        }
        return details.get(level, details[AutonomyLevel.SANDBOX])

    async def _calculate_progress(
        self,
        config: AIUserConfig,
        current_level: AutonomyLevel
    ) -> Dict[str, Any]:
        """
        Calculate progress toward next autonomy level.

        Returns progress metrics for each criterion.
        """
        if current_level == AutonomyLevel.AUTONOMOUS:
            # Already at max level
            return {
                "overall_percent": 100,
                "next_level": None,
                "criteria": {}
            }

        # Determine next level and its requirements
        if current_level == AutonomyLevel.SANDBOX:
            next_level = AutonomyLevel.SUPERVISED
            required_trades = GRADUATION_THRESHOLDS["min_trades"]
            required_win_rate = GRADUATION_THRESHOLDS["min_win_rate"]
        else:  # SUPERVISED -> AUTONOMOUS
            next_level = AutonomyLevel.AUTONOMOUS
            required_trades = GRADUATION_THRESHOLDS["min_trades"] * 2  # 50 trades
            required_win_rate = GRADUATION_THRESHOLDS["min_win_rate"]

        # Calculate individual progress
        trades_progress = min(100, (config.paper_trades_completed / required_trades) * 100)
        win_rate_progress = min(100, (float(config.paper_win_rate) / required_win_rate) * 100)
        pnl_progress = 100 if config.paper_total_pnl >= 0 else 0

        # Overall progress (average of all criteria)
        overall = (trades_progress + win_rate_progress + pnl_progress) / 3

        return {
            "overall_percent": round(overall, 1),
            "next_level": next_level.value,
            "next_level_name": self._get_level_details(next_level)["name"],
            "criteria": {
                "trades": {
                    "current": config.paper_trades_completed,
                    "required": required_trades,
                    "progress_percent": round(trades_progress, 1),
                    "met": config.paper_trades_completed >= required_trades
                },
                "win_rate": {
                    "current": float(config.paper_win_rate),
                    "required": required_win_rate,
                    "progress_percent": round(win_rate_progress, 1),
                    "met": float(config.paper_win_rate) >= required_win_rate
                },
                "pnl": {
                    "current": float(config.paper_total_pnl),
                    "required": 0,
                    "progress_percent": pnl_progress,
                    "met": config.paper_total_pnl >= 0
                }
            }
        }

    def _get_unlock_criteria(
        self,
        current_level: AutonomyLevel,
        config: AIUserConfig
    ) -> List[Dict[str, Any]]:
        """
        Get unlock criteria for next level as a checklist.
        """
        if current_level == AutonomyLevel.AUTONOMOUS:
            return []  # Already at max

        if current_level == AutonomyLevel.SANDBOX:
            required_trades = GRADUATION_THRESHOLDS["min_trades"]
            required_win_rate = GRADUATION_THRESHOLDS["min_win_rate"]
        else:
            required_trades = GRADUATION_THRESHOLDS["min_trades"] * 2
            required_win_rate = GRADUATION_THRESHOLDS["min_win_rate"]

        return [
            {
                "id": "trades",
                "label": f"Complete {required_trades}+ trades",
                "description": f"Currently: {config.paper_trades_completed} trades",
                "met": config.paper_trades_completed >= required_trades,
                "icon": "chart-line"
            },
            {
                "id": "win_rate",
                "label": f"Maintain {required_win_rate}%+ win rate",
                "description": f"Currently: {config.paper_win_rate}%",
                "met": float(config.paper_win_rate) >= required_win_rate,
                "icon": "percentage"
            },
            {
                "id": "pnl",
                "label": "Achieve positive P&L",
                "description": f"Currently: ₹{config.paper_total_pnl:,.2f}",
                "met": config.paper_total_pnl >= 0,
                "icon": "indian-rupee-sign"
            },
        ]

    async def _check_degradation(
        self,
        user_id: UUID,
        config: AIUserConfig
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        """
        Check for any degradation conditions or pause triggers.

        Returns:
            - List of warning objects
            - Boolean indicating if paused
            - Pause reason (if paused)
        """
        warnings = []
        is_paused = False
        pause_reason = None

        # Check drawdown
        if config.current_drawdown_pct >= DEGRADATION_THRESHOLDS["max_drawdown"]:
            warnings.append({
                "type": "critical",
                "reason": DegradationReason.HIGH_DRAWDOWN.value,
                "message": f"Drawdown at {config.current_drawdown_pct}% - trading paused",
                "threshold": float(DEGRADATION_THRESHOLDS["max_drawdown"])
            })
            is_paused = True
            pause_reason = "High drawdown limit exceeded"
        elif config.current_drawdown_pct >= DEGRADATION_THRESHOLDS["max_drawdown"] * Decimal("0.75"):
            warnings.append({
                "type": "warning",
                "reason": DegradationReason.HIGH_DRAWDOWN.value,
                "message": f"Drawdown at {config.current_drawdown_pct}% - approaching limit",
                "threshold": float(DEGRADATION_THRESHOLDS["max_drawdown"])
            })

        # Check win rate maintenance
        if float(config.paper_win_rate) < DEGRADATION_THRESHOLDS["min_win_rate_maintenance"]:
            if config.paper_trades_completed >= 10:  # Only warn after enough trades
                warnings.append({
                    "type": "warning",
                    "reason": DegradationReason.LOW_WIN_RATE.value,
                    "message": f"Win rate at {config.paper_win_rate}% - below maintenance threshold",
                    "threshold": DEGRADATION_THRESHOLDS["min_win_rate_maintenance"]
                })

        # Check risk state
        try:
            risk_state = await self._get_current_risk_state(user_id)
            if risk_state and risk_state.state == RiskState.PAUSED.value:
                warnings.append({
                    "type": "critical",
                    "reason": DegradationReason.RISK_STATE_PAUSED.value,
                    "message": "Risk state is PAUSED - trading halted",
                    "threshold": None
                })
                is_paused = True
                if not pause_reason:
                    pause_reason = risk_state.reason or "Risk state triggered pause"
        except Exception as e:
            logger.warning(f"Could not check risk state: {e}")

        # Check if AI is disabled
        if not config.ai_enabled:
            is_paused = True
            if not pause_reason:
                pause_reason = "AI trading is disabled"

        return warnings, is_paused, pause_reason

    async def _get_current_risk_state(self, user_id: UUID) -> Optional[AIRiskState]:
        """Get user's current risk state."""
        result = await self.db.execute(
            select(AIRiskState)
            .where(
                and_(
                    AIRiskState.user_id == user_id,
                    AIRiskState.resolved_at.is_(None)
                )
            )
            .order_by(AIRiskState.triggered_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _calculate_days_trading(self, start_date) -> int:
        """Calculate days since paper trading started."""
        if not start_date:
            return 0

        today = datetime.now(timezone.utc).date()
        delta = today - start_date
        return max(0, delta.days)

    def _get_default_status(self) -> Dict[str, Any]:
        """Return default status for users without AI config."""
        return {
            "current_level": AutonomyLevel.SANDBOX.value,
            "level_index": 0,
            "level_details": self._get_level_details(AutonomyLevel.SANDBOX),
            "progress": {
                "overall_percent": 0,
                "next_level": AutonomyLevel.SUPERVISED.value,
                "next_level_name": "Supervised",
                "criteria": {}
            },
            "unlock_criteria": [],
            "warnings": [],
            "is_paused": True,
            "pause_reason": "AI configuration not found",
            "ai_enabled": False,
            "graduation_approved": False,
            "stats": {
                "trades_completed": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "days_trading": 0,
                "current_drawdown": 0,
            }
        }

    async def get_level_history(
        self,
        user_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get history of autonomy level changes.

        Currently returns placeholder - would need to track level transitions
        in a dedicated table for full history.
        """
        # For now, return current level as only history entry
        config = await self._get_user_config(user_id)
        if not config:
            return []

        current_level = self._determine_level(config)

        return [
            {
                "level": current_level.value,
                "level_name": self._get_level_details(current_level)["name"],
                "timestamp": config.created_at.isoformat() if config.created_at else datetime.now(timezone.utc).isoformat(),
                "reason": "Initial configuration"
            }
        ]


__all__ = [
    "AutonomyStatusService",
    "AutonomyLevel",
    "DegradationReason",
    "GRADUATION_THRESHOLDS",
    "DEGRADATION_THRESHOLDS",
]
