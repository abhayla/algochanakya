"""
Condition Engine

Evaluates entry conditions for AutoPilot strategies.
Supports time, price, VIX, premium, and custom conditions.
"""
import asyncio
from datetime import datetime, time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class ConditionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class ConditionLogic(str, Enum):
    AND = "AND"
    OR = "OR"


@dataclass
class ConditionResult:
    """Result of evaluating a single condition."""
    condition_id: str
    variable: str
    operator: str
    target_value: Any
    current_value: Any
    is_met: bool
    progress_pct: Optional[float] = None
    distance_to_trigger: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of evaluating all conditions."""
    strategy_id: int
    all_conditions_met: bool
    individual_results: List[ConditionResult]
    evaluation_time: datetime
    error: Optional[str] = None


class ConditionEngine:
    """
    Evaluates strategy entry conditions.

    Supported variables:
    - TIME.CURRENT: Current time (HH:MM format)
    - TIME.MINUTES_SINCE_OPEN: Minutes since market open
    - SPOT.{UNDERLYING}: Spot price (e.g., SPOT.NIFTY)
    - SPOT.{UNDERLYING}.CHANGE_PCT: Spot change percentage
    - VIX.VALUE: India VIX current value
    - VIX.CHANGE: VIX change from previous close
    - PREMIUM.{LEG_ID}: Premium of specific leg
    - WEEKDAY: Current weekday (MON, TUE, etc.)
    """

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self._previous_values: Dict[str, Any] = {}  # For crosses_above/below

    async def evaluate(
        self,
        strategy_id: int,
        entry_conditions: Dict[str, Any],
        underlying: str,
        legs_config: List[Dict[str, Any]]
    ) -> EvaluationResult:
        """
        Evaluate all entry conditions for a strategy.

        Args:
            strategy_id: Strategy ID
            entry_conditions: Entry conditions config from strategy
            underlying: Strategy underlying (NIFTY, BANKNIFTY, etc.)
            legs_config: Legs configuration for premium conditions

        Returns:
            EvaluationResult with all condition evaluations
        """
        try:
            logic = ConditionLogic(entry_conditions.get('logic', 'AND'))
            conditions = entry_conditions.get('conditions', [])

            if not conditions:
                # No conditions = always met
                return EvaluationResult(
                    strategy_id=strategy_id,
                    all_conditions_met=True,
                    individual_results=[],
                    evaluation_time=datetime.now()
                )

            # Evaluate each condition
            results: List[ConditionResult] = []
            for condition in conditions:
                if not condition.get('enabled', True):
                    continue

                result = await self._evaluate_condition(
                    condition=condition,
                    underlying=underlying,
                    legs_config=legs_config
                )
                results.append(result)

            # Apply logic (AND/OR)
            if logic == ConditionLogic.AND:
                all_met = all(r.is_met for r in results)
            else:  # OR
                all_met = any(r.is_met for r in results) if results else True

            return EvaluationResult(
                strategy_id=strategy_id,
                all_conditions_met=all_met,
                individual_results=results,
                evaluation_time=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error evaluating conditions for strategy {strategy_id}: {e}")
            return EvaluationResult(
                strategy_id=strategy_id,
                all_conditions_met=False,
                individual_results=[],
                evaluation_time=datetime.now(),
                error=str(e)
            )

    async def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        underlying: str,
        legs_config: List[Dict[str, Any]]
    ) -> ConditionResult:
        """Evaluate a single condition."""
        condition_id = condition.get('id', 'unknown')
        variable = condition.get('variable', '')
        operator = condition.get('operator', 'equals')
        target_value = condition.get('value')

        try:
            # Get current value based on variable type
            current_value = await self._get_variable_value(
                variable=variable,
                underlying=underlying,
                legs_config=legs_config
            )

            # Compare values
            is_met = self._compare_values(
                current=current_value,
                target=target_value,
                operator=ConditionOperator(operator),
                variable=variable
            )

            # Calculate progress percentage
            progress_pct = self._calculate_progress(
                current=current_value,
                target=target_value,
                operator=operator,
                variable=variable
            )

            # Calculate distance to trigger
            distance = self._calculate_distance(
                current=current_value,
                target=target_value,
                operator=operator,
                variable=variable
            )

            return ConditionResult(
                condition_id=condition_id,
                variable=variable,
                operator=operator,
                target_value=target_value,
                current_value=current_value,
                is_met=is_met,
                progress_pct=progress_pct,
                distance_to_trigger=distance
            )

        except Exception as e:
            logger.error(f"Error evaluating condition {condition_id}: {e}")
            return ConditionResult(
                condition_id=condition_id,
                variable=variable,
                operator=operator,
                target_value=target_value,
                current_value=None,
                is_met=False,
                error=str(e)
            )

    async def _get_variable_value(
        self,
        variable: str,
        underlying: str,
        legs_config: List[Dict[str, Any]]
    ) -> Any:
        """Get current value for a variable."""

        # TIME variables
        if variable == "TIME.CURRENT":
            return datetime.now().strftime("%H:%M")

        if variable == "TIME.MINUTES_SINCE_OPEN":
            now = datetime.now()
            market_open = datetime.combine(now.date(), self.MARKET_OPEN)
            if now < market_open:
                return 0
            return int((now - market_open).total_seconds() / 60)

        # WEEKDAY
        if variable == "WEEKDAY":
            return datetime.now().strftime("%a").upper()[:3]  # MON, TUE, etc.

        # SPOT variables
        if variable.startswith("SPOT."):
            parts = variable.split(".")
            spot_underlying = parts[1] if len(parts) > 1 else underlying

            spot_data = await self.market_data.get_spot_price(spot_underlying)

            if len(parts) == 2:
                return float(spot_data.ltp)
            elif len(parts) == 3 and parts[2] == "CHANGE_PCT":
                return spot_data.change_pct

        # VIX variables
        if variable.startswith("VIX."):
            vix_value = await self.market_data.get_vix()

            if variable == "VIX.VALUE":
                return float(vix_value)
            elif variable == "VIX.CHANGE":
                # Would need previous close, return 0 for now
                return 0.0

        # PREMIUM variables (e.g., PREMIUM.leg_1)
        if variable.startswith("PREMIUM."):
            leg_id = variable.split(".")[1]
            # Find the leg in config
            for leg in legs_config:
                if leg.get('id') == leg_id:
                    # Get premium from leg's tradingsymbol
                    tradingsymbol = leg.get('tradingsymbol')
                    if tradingsymbol:
                        ltp_data = await self.market_data.get_ltp([f"NFO:{tradingsymbol}"])
                        return float(ltp_data.get(f"NFO:{tradingsymbol}", 0))
            return 0.0

        raise ValueError(f"Unknown variable: {variable}")

    def _compare_values(
        self,
        current: Any,
        target: Any,
        operator: ConditionOperator,
        variable: str
    ) -> bool:
        """Compare current value against target using operator."""

        # Handle time comparisons
        if variable.startswith("TIME.CURRENT"):
            current = self._parse_time(current)
            target = self._parse_time(target)

        # Handle numeric comparisons
        if isinstance(current, (int, float)) and isinstance(target, (int, float, str)):
            if isinstance(target, str):
                try:
                    target = float(target)
                except ValueError:
                    return False
            current = float(current)

        # Comparison logic
        if operator == ConditionOperator.EQUALS:
            return current == target

        elif operator == ConditionOperator.NOT_EQUALS:
            return current != target

        elif operator == ConditionOperator.GREATER_THAN:
            return current > target

        elif operator == ConditionOperator.LESS_THAN:
            return current < target

        elif operator == ConditionOperator.GREATER_EQUAL:
            return current >= target

        elif operator == ConditionOperator.LESS_EQUAL:
            return current <= target

        elif operator == ConditionOperator.BETWEEN:
            if isinstance(target, list) and len(target) == 2:
                return target[0] <= current <= target[1]
            return False

        elif operator == ConditionOperator.NOT_BETWEEN:
            if isinstance(target, list) and len(target) == 2:
                return not (target[0] <= current <= target[1])
            return True

        elif operator == ConditionOperator.CROSSES_ABOVE:
            prev = self._previous_values.get(variable)
            self._previous_values[variable] = current
            if prev is None:
                return False
            return prev < target <= current

        elif operator == ConditionOperator.CROSSES_BELOW:
            prev = self._previous_values.get(variable)
            self._previous_values[variable] = current
            if prev is None:
                return False
            return prev > target >= current

        return False

    def _calculate_progress(
        self,
        current: Any,
        target: Any,
        operator: str,
        variable: str
    ) -> Optional[float]:
        """Calculate progress percentage towards condition being met."""
        try:
            # Handle time comparison
            if variable.startswith("TIME.CURRENT"):
                current_mins = self._parse_time(current)
                target_mins = self._parse_time(target)
                market_open_mins = self.MARKET_OPEN.hour * 60 + self.MARKET_OPEN.minute

                if operator in ["greater_than", "greater_equal"]:
                    total_distance = target_mins - market_open_mins
                    current_distance = current_mins - market_open_mins
                    if total_distance > 0:
                        return min(100, max(0, (current_distance / total_distance) * 100))

            # Numeric comparisons
            if isinstance(current, (int, float)) and isinstance(target, (int, float, str)):
                current = float(current)
                target = float(target) if isinstance(target, str) else target

                if operator in ["greater_than", "greater_equal"]:
                    if target > 0:
                        return min(100, max(0, (current / target) * 100))
                elif operator in ["less_than", "less_equal"]:
                    if current > 0:
                        return min(100, max(0, (target / current) * 100))

            return None
        except Exception:
            return None

    def _calculate_distance(
        self,
        current: Any,
        target: Any,
        operator: str,
        variable: str
    ) -> Optional[str]:
        """Calculate distance to trigger (human-readable)."""
        try:
            # Handle time
            if variable.startswith("TIME.CURRENT"):
                current_mins = self._parse_time(current)
                target_mins = self._parse_time(target)
                diff = target_mins - current_mins

                if diff > 0:
                    hours = diff // 60
                    mins = diff % 60
                    if hours > 0:
                        return f"{hours}h {mins}m"
                    return f"{mins}m"
                elif diff == 0:
                    return "Now"
                else:
                    return "Passed"

            # Numeric comparisons
            if isinstance(current, (int, float)) and isinstance(target, (int, float, str)):
                current = float(current)
                target = float(target) if isinstance(target, str) else target
                diff = target - current

                if abs(diff) < 1:
                    return f"{diff:+.2f}"
                elif abs(diff) < 100:
                    return f"{diff:+.1f}"
                else:
                    return f"{diff:+.0f}"

            return None
        except Exception:
            return None

    def _parse_time(self, time_str: str) -> int:
        """Parse time string to minutes since midnight."""
        if isinstance(time_str, int):
            return time_str
        if not time_str or not isinstance(time_str, str):
            return 0
        parts = time_str.split(":")
        if len(parts) >= 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0

    def clear_previous_values(self):
        """Clear cached previous values (used for crosses_above/below)."""
        self._previous_values.clear()


# Service instance cache
_condition_engines: Dict[str, ConditionEngine] = {}


def get_condition_engine(market_data: MarketDataService) -> ConditionEngine:
    """Get or create ConditionEngine instance."""
    # Use market_data's kite access token as key
    token_key = market_data.kite.access_token or "default"

    if token_key not in _condition_engines:
        _condition_engines[token_key] = ConditionEngine(market_data)

    return _condition_engines[token_key]


def clear_condition_engines():
    """Clear all cached engine instances."""
    global _condition_engines
    _condition_engines.clear()
