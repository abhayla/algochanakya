"""
Condition Engine - Phase 5C

Evaluates entry conditions for AutoPilot strategies.
Supports time, price, VIX, premium, OI, IV, probability, and custom conditions.

Phase 5C Additions:
- OI.PCR, OI.MAX_PAIN, OI.CHANGE
- PROBABILITY.OTM
- STRATEGY.DTE
"""
import asyncio
from datetime import datetime, time, date
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
    - STRATEGY.DELTA/GAMMA/THETA/VEGA: Net position Greeks (Phase 5A)
    - SPOT.DISTANCE_TO.BREAKEVEN: Distance to nearest breakeven (Phase 5B #52)
    - SPOT.DISTANCE_TO.{LEG_ID}: Distance to specific leg strike (Phase 5B #48)
    - PREMIUM.CAPTURED_PCT: Premium captured percentage (Phase 5B #50)
    - STRATEGY.THETA_BURN_RATE: Actual vs expected theta (Phase 5B #51)
    - IV.RANK: IV Rank (0-100) (Phase 5B #53)
    - IV.PERCENTILE: IV Percentile (Phase 5B #53)

    Phase 5C: Entry Enhancements (#6-11, #14, #24)
    - OI.PCR: Put-Call Ratio (Phase 5C #6)
    - OI.MAX_PAIN: Max Pain strike price (Phase 5C #7)
    - OI.CHANGE: OI change percentage (Phase 5C #8)
    - PROBABILITY.OTM: Min Probability OTM across legs (Phase 5C #11)
    - PROBABILITY.OTM.{LEG_ID}: Probability OTM for specific leg (Phase 5C #11)
    - STRATEGY.DTE: Days to expiry (Phase 5C #14)
    - STRATEGY.DAYS_IN_TRADE: Days since entry (Phase 5C #24)
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
        legs_config: List[Dict[str, Any]],
        greeks_snapshot: Optional[Dict[str, float]] = None
    ) -> EvaluationResult:
        """
        Evaluate all entry conditions for a strategy.

        Supports both flat conditions and nested condition groups.

        Flat structure (backward compatible):
        {
            "logic": "AND",
            "conditions": [{"variable": "...", "operator": "...", "value": ...}]
        }

        Nested structure (Phase 5C #17):
        {
            "logic": "OR",
            "groups": [
                {
                    "logic": "AND",
                    "conditions": [...]
                },
                {
                    "logic": "AND",
                    "conditions": [...]
                }
            ]
        }

        Args:
            strategy_id: Strategy ID
            entry_conditions: Entry conditions config from strategy
            underlying: Strategy underlying (NIFTY, BANKNIFTY, etc.)
            legs_config: Legs configuration for premium conditions
            greeks_snapshot: Optional Greeks snapshot (delta, gamma, theta, vega)

        Returns:
            EvaluationResult with all condition evaluations
        """
        try:
            # Check if using nested groups structure
            if 'groups' in entry_conditions:
                return await self._evaluate_nested_groups(
                    strategy_id=strategy_id,
                    entry_conditions=entry_conditions,
                    underlying=underlying,
                    legs_config=legs_config,
                    greeks_snapshot=greeks_snapshot
                )

            # Original flat structure (backward compatible)
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
                    legs_config=legs_config,
                    greeks_snapshot=greeks_snapshot
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

    async def _evaluate_nested_groups(
        self,
        strategy_id: int,
        entry_conditions: Dict[str, Any],
        underlying: str,
        legs_config: List[Dict[str, Any]],
        greeks_snapshot: Optional[Dict[str, float]] = None
    ) -> EvaluationResult:
        """
        Evaluate nested condition groups (Phase 5C #17).

        Example: (Group1 AND Group2) OR (Group3)
        Where each group has its own logic and conditions.

        Args:
            Same as evaluate()

        Returns:
            EvaluationResult with flattened results from all groups
        """
        try:
            top_level_logic = ConditionLogic(entry_conditions.get('logic', 'OR'))
            groups = entry_conditions.get('groups', [])

            if not groups:
                return EvaluationResult(
                    strategy_id=strategy_id,
                    all_conditions_met=True,
                    individual_results=[],
                    evaluation_time=datetime.now()
                )

            group_results = []
            all_individual_results = []

            # Evaluate each group
            for group in groups:
                group_logic = ConditionLogic(group.get('logic', 'AND'))
                conditions = group.get('conditions', [])

                group_individual_results = []

                # Evaluate conditions in this group
                for condition in conditions:
                    if not condition.get('enabled', True):
                        continue

                    result = await self._evaluate_condition(
                        condition=condition,
                        underlying=underlying,
                        legs_config=legs_config,
                        greeks_snapshot=greeks_snapshot
                    )
                    group_individual_results.append(result)
                    all_individual_results.append(result)

                # Apply group logic
                if group_logic == ConditionLogic.AND:
                    group_met = all(r.is_met for r in group_individual_results) if group_individual_results else True
                else:  # OR
                    group_met = any(r.is_met for r in group_individual_results) if group_individual_results else False

                group_results.append(group_met)

            # Apply top-level logic across groups
            if top_level_logic == ConditionLogic.AND:
                all_met = all(group_results)
            else:  # OR
                all_met = any(group_results) if group_results else False

            logger.info(
                f"Nested groups evaluation: Top logic={top_level_logic.value}, "
                f"Group results={group_results}, Final={all_met}"
            )

            return EvaluationResult(
                strategy_id=strategy_id,
                all_conditions_met=all_met,
                individual_results=all_individual_results,
                evaluation_time=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error evaluating nested groups for strategy {strategy_id}: {e}")
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
        legs_config: List[Dict[str, Any]],
        greeks_snapshot: Optional[Dict[str, float]] = None
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
                legs_config=legs_config,
                greeks_snapshot=greeks_snapshot
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
        legs_config: List[Dict[str, Any]],
        greeks_snapshot: Optional[Dict[str, float]] = None
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

        # STRATEGY GREEKS variables (Phase 5A)
        # Greeks are calculated by strategy_monitor and passed via greeks_snapshot
        if variable == "STRATEGY.DELTA":
            if greeks_snapshot:
                return float(greeks_snapshot.get('delta', 0.0))
            return 0.0

        if variable == "STRATEGY.GAMMA":
            if greeks_snapshot:
                return float(greeks_snapshot.get('gamma', 0.0))
            return 0.0

        if variable == "STRATEGY.THETA":
            if greeks_snapshot:
                return float(greeks_snapshot.get('theta', 0.0))
            return 0.0

        if variable == "STRATEGY.VEGA":
            if greeks_snapshot:
                return float(greeks_snapshot.get('vega', 0.0))
            return 0.0

        # Phase 5B: BREAKEVEN DISTANCE (#52)
        if variable == "SPOT.DISTANCE_TO.BREAKEVEN":
            if greeks_snapshot and 'breakevens' in greeks_snapshot:
                breakevens = greeks_snapshot['breakevens']
                spot = await self.market_data.get_spot_price(underlying)
                spot_price = float(spot.ltp)

                lower_be = breakevens.get('lower')
                upper_be = breakevens.get('upper')

                if lower_be and upper_be:
                    # Return distance to nearest breakeven as percentage
                    distance_lower = abs(spot_price - float(lower_be)) / spot_price * 100
                    distance_upper = abs(spot_price - float(upper_be)) / spot_price * 100
                    return min(distance_lower, distance_upper)
            return 100.0  # If no breakevens, return large value

        # Phase 5B: SPOT DISTANCE TO LEG (#48)
        if variable.startswith("SPOT.DISTANCE_TO."):
            leg_id = variable.split(".")[-1]
            # Find the leg in config
            for leg in legs_config:
                if leg.get('id') == leg_id or leg.get('leg_id') == leg_id:
                    strike = float(leg.get('strike', 0))
                    spot = await self.market_data.get_spot_price(underlying)
                    spot_price = float(spot.ltp)

                    if strike > 0 and spot_price > 0:
                        # Return distance as percentage
                        distance_pct = abs(spot_price - strike) / spot_price * 100
                        return distance_pct
            return 100.0  # If leg not found, return large value

        # Phase 5B: PREMIUM CAPTURED PERCENTAGE (#50)
        if variable == "PREMIUM.CAPTURED_PCT":
            if greeks_snapshot and 'entry_premium' in greeks_snapshot and 'current_value' in greeks_snapshot:
                entry_premium = float(greeks_snapshot['entry_premium'])
                current_value = float(greeks_snapshot['current_value'])

                if entry_premium > 0:
                    # For credit strategies, premium captured = (entry - current) / entry
                    captured_pct = ((entry_premium - current_value) / entry_premium) * 100
                    return max(0, captured_pct)  # Don't return negative
            return 0.0

        # Phase 5B: THETA BURN RATE (#51)
        if variable == "STRATEGY.THETA_BURN_RATE":
            if greeks_snapshot and 'theta_tracking' in greeks_snapshot:
                theta_tracking = greeks_snapshot['theta_tracking']
                return float(theta_tracking.get('actual_vs_expected_pct', 0.0))
            return 0.0

        # Phase 5B: IV RANK (#53)
        if variable == "IV.RANK":
            if greeks_snapshot and 'iv_rank' in greeks_snapshot:
                return float(greeks_snapshot['iv_rank'])
            return 0.0

        # Phase 5B: IV PERCENTILE (#53)
        if variable == "IV.PERCENTILE":
            if greeks_snapshot and 'iv_percentile' in greeks_snapshot:
                return float(greeks_snapshot['iv_percentile'])
            return 0.0

        # ===== PHASE 5C: ENTRY ENHANCEMENTS =====

        # Phase 5C: OI.PCR - Put-Call Ratio (#6)
        if variable == "OI.PCR":
            if greeks_snapshot and 'oi_pcr' in greeks_snapshot:
                return float(greeks_snapshot['oi_pcr'])
            return 0.0

        # Phase 5C: OI.MAX_PAIN - Max Pain Strike (#7)
        if variable == "OI.MAX_PAIN":
            if greeks_snapshot and 'oi_max_pain' in greeks_snapshot:
                return float(greeks_snapshot['oi_max_pain'])
            return 0.0

        # Phase 5C: OI.CHANGE - OI Change Percentage (#8)
        if variable == "OI.CHANGE" or variable.startswith("OI.CHANGE."):
            if greeks_snapshot and 'oi_change' in greeks_snapshot:
                # Can be overall OI change or per-strike
                if variable == "OI.CHANGE":
                    return float(greeks_snapshot['oi_change'])
                else:
                    # OI.CHANGE.STRIKE.24500.CE format
                    strike_info = variable.split(".")
                    if len(strike_info) >= 4:
                        strike = strike_info[2]
                        option_type = strike_info[3]
                        key = f"oi_change_{strike}_{option_type}"
                        if key in greeks_snapshot:
                            return float(greeks_snapshot[key])
            return 0.0

        # Phase 5C: PROBABILITY.OTM - Probability Out-of-The-Money (#11)
        if variable.startswith("PROBABILITY.OTM"):
            if greeks_snapshot and 'probability_otm' in greeks_snapshot:
                # Can be for specific leg or average
                if variable == "PROBABILITY.OTM":
                    # Return minimum probability OTM across all legs (most conservative)
                    return float(greeks_snapshot['probability_otm'])
                else:
                    # PROBABILITY.OTM.LEG_ID format
                    leg_id = variable.split(".")[-1]
                    key = f"probability_otm_{leg_id}"
                    if key in greeks_snapshot:
                        return float(greeks_snapshot[key])
            return 0.0

        # Phase 5C: STRATEGY.DTE - Days to Expiry (#14)
        if variable == "STRATEGY.DTE":
            if greeks_snapshot and 'dte' in greeks_snapshot:
                return int(greeks_snapshot['dte'])

            # Fallback: Calculate from legs config
            if legs_config:
                for leg in legs_config:
                    expiry = leg.get('expiry')
                    if expiry:
                        try:
                            if isinstance(expiry, str):
                                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                            elif isinstance(expiry, date):
                                expiry_date = expiry
                            elif isinstance(expiry, datetime):
                                expiry_date = expiry.date()
                            else:
                                continue

                            today = date.today()
                            dte = (expiry_date - today).days
                            return max(0, dte)
                        except Exception as e:
                            logger.error(f"Error calculating DTE: {e}")
                            continue
            return 0

        # Phase 5C: STRATEGY.DAYS_IN_TRADE - Days since entry (#24)
        if variable == "STRATEGY.DAYS_IN_TRADE":
            if greeks_snapshot and 'days_in_trade' in greeks_snapshot:
                return int(greeks_snapshot['days_in_trade'])

            # Fallback: Calculate from entry time
            if greeks_snapshot and 'entry_time' in greeks_snapshot:
                try:
                    entry_time = greeks_snapshot['entry_time']
                    if isinstance(entry_time, str):
                        entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                    elif isinstance(entry_time, datetime):
                        entry_dt = entry_time
                    else:
                        return 0

                    now = datetime.now(entry_dt.tzinfo) if entry_dt.tzinfo else datetime.now()
                    days_in_trade = (now - entry_dt).days
                    return max(0, days_in_trade)
                except Exception as e:
                    logger.error(f"Error calculating days in trade: {e}")
            return 0

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
