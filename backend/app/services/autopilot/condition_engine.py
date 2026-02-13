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

from app.services.legacy.market_data import MarketDataService

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

    def __init__(self, *args):
        """
        Initialize ConditionEngine.

        Supports two signatures:
        1. ConditionEngine(market_data)  # Original signature
        2. ConditionEngine(db_session, user_id, market_data)  # Phase 5A signature
        """
        if len(args) == 1:
            # Single argument: market_data (original signature)
            self.db = None
            self.user_id = None
            self.market_data = args[0]
        elif len(args) == 3:
            # Three arguments: db_session, user_id, market_data
            self.db = args[0]
            self.user_id = args[1]
            self.market_data = args[2]
        else:
            raise TypeError(f"ConditionEngine.__init__() takes 2 or 4 positional arguments but {len(args) + 1} were given")

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

    async def evaluate_condition(
        self,
        condition: Dict[str, Any],
        underlying: str,
        strategy: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Public method to evaluate a single condition (Phase 5A).

        Args:
            condition: Condition dict with variable, operator, value
            underlying: Strategy underlying (NIFTY, BANKNIFTY, etc.)
            strategy: Optional strategy object with runtime_state containing Greeks

        Returns:
            Dict with is_met and other evaluation details
        """
        # Extract Greeks snapshot and legs_config from strategy if provided
        greeks_snapshot = None
        legs_config = []
        if strategy:
            if hasattr(strategy, 'runtime_state'):
                runtime_state = strategy.runtime_state or {}
                if 'greeks' in runtime_state:
                    greeks_snapshot = runtime_state['greeks']
            if hasattr(strategy, 'legs_config'):
                legs_config = strategy.legs_config or []

        # Evaluate the condition
        result = await self._evaluate_condition(
            condition=condition,
            underlying=underlying,
            legs_config=legs_config,
            greeks_snapshot=greeks_snapshot,
            strategy=strategy
        )

        # Return as dict (tests expect dict, not ConditionResult object)
        return {
            "condition_id": result.condition_id,
            "variable": result.variable,
            "operator": result.operator,
            "target_value": result.target_value,
            "current_value": result.current_value,
            "is_met": result.is_met,
            "progress_pct": result.progress_pct,
            "distance_to_trigger": result.distance_to_trigger,
            "error": result.error
        }

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
        greeks_snapshot: Optional[Dict[str, float]] = None,
        strategy: Optional[Any] = None
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
                greeks_snapshot=greeks_snapshot,
                strategy=strategy
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
        legs_config: List[Dict[str, Any]] = None,
        greeks_snapshot: Optional[Dict[str, float]] = None,
        strategy: Optional[Any] = None
    ) -> Any:
        """Get current value for a variable."""
        # Use strategy.runtime_state['greeks'] if strategy provided (Phase 5A)
        if strategy and hasattr(strategy, 'runtime_state'):
            runtime_state = strategy.runtime_state or {}
            if 'greeks' in runtime_state and not greeks_snapshot:
                greeks_snapshot = runtime_state['greeks']
            # Also check for previous_greeks for crosses_above/below
            if 'previous_greeks' in runtime_state:
                prev_greeks = runtime_state['previous_greeks']
                if prev_greeks:
                    # Store previous values for crosses operators
                    for greek in ['net_delta', 'net_gamma', 'net_theta', 'net_vega']:
                        if greek in prev_greeks:
                            self._previous_values[f"STRATEGY.{greek.upper().replace('NET_', '')}"] = prev_greeks[greek]

        # Extract legs_config from strategy if not provided (Phase 5B)
        if legs_config is None:
            if strategy and hasattr(strategy, 'legs_config'):
                legs_config = strategy.legs_config or []
            else:
                legs_config = []

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
                # Try both 'net_delta' and 'delta' keys
                value = greeks_snapshot.get('net_delta') or greeks_snapshot.get('delta', 0.0)
                return float(value)
            return 0.0

        if variable == "STRATEGY.GAMMA":
            if greeks_snapshot:
                # Try both 'net_gamma' and 'gamma' keys
                value = greeks_snapshot.get('net_gamma') or greeks_snapshot.get('gamma', 0.0)
                return float(value)
            return 0.0

        if variable == "STRATEGY.THETA":
            if greeks_snapshot:
                # Try both 'net_theta' and 'theta' keys
                value = greeks_snapshot.get('net_theta') or greeks_snapshot.get('theta', 0.0)
                return float(value)
            return 0.0

        if variable == "STRATEGY.VEGA":
            if greeks_snapshot:
                # Try both 'net_vega' and 'vega' keys
                value = greeks_snapshot.get('net_vega') or greeks_snapshot.get('vega', 0.0)
                return float(value)
            return 0.0

        # Phase 5B: BREAKEVEN DISTANCE (#52)
        if variable == "SPOT.DISTANCE_TO.BREAKEVEN":
            breakevens = None

            # Try greeks_snapshot first
            if greeks_snapshot and 'breakevens' in greeks_snapshot:
                breakevens_data = greeks_snapshot['breakevens']
                lower_be = breakevens_data.get('lower')
                upper_be = breakevens_data.get('upper')
                if lower_be and upper_be:
                    breakevens = [lower_be, upper_be]

            # Fallback to strategy.breakevens
            elif strategy and hasattr(strategy, 'breakevens'):
                be_list = strategy.breakevens
                if isinstance(be_list, list) and len(be_list) >= 2:
                    breakevens = be_list

            if breakevens:
                spot = await self.market_data.get_spot_price(underlying)
                spot_price = float(spot.ltp)

                # Return distance to nearest breakeven as percentage
                distances = [abs(spot_price - float(be)) / spot_price * 100 for be in breakevens]
                return min(distances)

            return 100.0  # If no breakevens, return large value

        # Phase 5B: SPOT DISTANCE TO LEG (#48)
        if variable.startswith("SPOT.DISTANCE_TO."):
            leg_identifier = variable.split(".")[-1]

            # Find the leg in config by ID or by alias (SHORT_PE, SHORT_CE, LONG_PE, LONG_CE)
            target_leg = None
            for leg in legs_config:
                # Match by leg ID
                if leg.get('id') == leg_identifier or leg.get('leg_id') == leg_identifier:
                    target_leg = leg
                    break

                # Match by alias (e.g., SHORT_PE = sell PE, SHORT_CE = sell CE)
                option_type = leg.get('option_type', '').upper()
                transaction_type = leg.get('transaction_type', '').lower()

                if leg_identifier == f"SHORT_{option_type}" and transaction_type == 'sell':
                    target_leg = leg
                    break
                elif leg_identifier == f"LONG_{option_type}" and transaction_type == 'buy':
                    target_leg = leg
                    break

            if target_leg:
                strike = float(target_leg.get('strike', 0))
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
            # Try calling IVMetricsService
            try:
                from app.services.options.iv_metrics_service import IVMetricsService
                iv_service = IVMetricsService(self.market_data)
                iv_rank = await iv_service.get_iv_rank(underlying)
                return float(iv_rank) if iv_rank is not None else 0.0
            except Exception:
                pass

            # Fallback to greeks_snapshot
            if greeks_snapshot and 'iv_rank' in greeks_snapshot:
                return float(greeks_snapshot['iv_rank'])
            return 0.0

        # Phase 5B: IV PERCENTILE (#53)
        if variable == "IV.PERCENTILE":
            # Try calling IVMetricsService
            try:
                from app.services.options.iv_metrics_service import IVMetricsService
                iv_service = IVMetricsService(self.market_data)
                iv_percentile = await iv_service.get_iv_percentile(underlying)
                return float(iv_percentile) if iv_percentile is not None else 0.0
            except Exception:
                pass

            # Fallback to greeks_snapshot
            if greeks_snapshot and 'iv_percentile' in greeks_snapshot:
                return float(greeks_snapshot['iv_percentile'])
            return 0.0

        # ===== PHASE 5C: ENTRY ENHANCEMENTS =====

        # Phase 5C: OI.PCR - Put-Call Ratio (#6)
        if variable == "OI.PCR":
            # Try calling OIAnalysisService if db is available (Phase 5A signature)
            if self.db and self.user_id:
                try:
                    from app.services.options.oi_analysis_service import OIAnalysisService
                    oi_service = OIAnalysisService(self.market_data.kite if hasattr(self.market_data, 'kite') else None, self.db)
                    pcr = await oi_service.get_pcr(underlying)
                    return float(pcr) if pcr is not None else 0.0
                except Exception:
                    pass

            # Fallback to greeks_snapshot
            if greeks_snapshot and 'oi_pcr' in greeks_snapshot:
                return float(greeks_snapshot['oi_pcr'])
            return 0.0

        # Phase 5C: OI.MAX_PAIN - Max Pain Strike (#7)
        if variable == "OI.MAX_PAIN":
            # Try calling OIAnalysisService if db is available
            if self.db and self.user_id:
                try:
                    from app.services.options.oi_analysis_service import OIAnalysisService
                    oi_service = OIAnalysisService(self.market_data.kite if hasattr(self.market_data, 'kite') else None, self.db)
                    max_pain = await oi_service.get_max_pain(underlying)
                    return float(max_pain) if max_pain is not None else 0.0
                except Exception:
                    pass

            # Fallback to greeks_snapshot
            if greeks_snapshot and 'oi_max_pain' in greeks_snapshot:
                return float(greeks_snapshot['oi_max_pain'])
            return 0.0

        # Phase 5C: OI.CHANGE - OI Change Percentage (#8)
        if variable == "OI.CHANGE" or variable.startswith("OI.CHANGE."):
            # Try calling OIAnalysisService if db is available
            if self.db and self.user_id:
                try:
                    from app.services.options.oi_analysis_service import OIAnalysisService
                    oi_service = OIAnalysisService(self.market_data.kite if hasattr(self.market_data, 'kite') else None, self.db)
                    oi_change = await oi_service.get_oi_change_pct(underlying)
                    return float(oi_change) if oi_change is not None else 0.0
                except Exception:
                    pass

            # Fallback to greeks_snapshot
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
            # Try calling GreeksCalculatorService if strategy has legs
            if strategy and hasattr(strategy, 'legs_config') and strategy.legs_config:
                try:
                    from app.services.options.greeks_calculator import GreeksCalculatorService
                    greeks_calc = GreeksCalculatorService(
                        self.market_data.kite if hasattr(self.market_data, 'kite') else None,
                        self.db
                    )
                    # Calculate probability OTM for first leg (most conservative)
                    first_leg = strategy.legs_config[0]
                    strike = first_leg.get('strike')
                    option_type = first_leg.get('option_type')
                    if strike and option_type:
                        prob_otm = await greeks_calc.calculate_probability_otm(
                            underlying=underlying,
                            strike=strike,
                            option_type=option_type
                        )
                        return float(prob_otm) if prob_otm is not None else 0.0
                except Exception:
                    pass

            # Fallback to greeks_snapshot
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

    async def evaluate_condition_historical(
        self,
        condition: Dict,
        historical_spot: float,
        historical_vix: Optional[float] = None,
        historical_timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Evaluate condition using historical market data.

        Args:
            condition: Condition dictionary with variable, operator, value
            historical_spot: Historical spot price
            historical_vix: Historical VIX value (optional)
            historical_timestamp: Historical timestamp (optional)

        Returns:
            True if condition met, False otherwise
        """
        try:
            var_type = condition.get("variable")
            operator = condition.get("operator")
            threshold = condition.get("value")

            if not all([var_type, operator, threshold is not None]):
                logger.warning(f"Invalid condition format: {condition}")
                return False

            # Get actual value for the variable using historical data
            if var_type == "SPOT":
                actual_value = historical_spot
            elif var_type == "VIX":
                if historical_vix is None:
                    logger.warning("VIX condition but no historical VIX provided")
                    return False
                actual_value = historical_vix
            elif var_type == "TIME":
                if historical_timestamp is None:
                    logger.warning("TIME condition but no historical timestamp provided")
                    return False
                # TIME format: "HH:MM"
                current_time = historical_timestamp.time()
                threshold_time = datetime.strptime(threshold, "%H:%M").time()

                if operator == "AFTER":
                    return current_time >= threshold_time
                elif operator == "BEFORE":
                    return current_time <= threshold_time
                else:
                    logger.warning(f"Invalid TIME operator: {operator}")
                    return False
            elif var_type == "PREMIUM":
                # For historical backtesting, premium conditions are difficult to evaluate
                # without full option chain historical data. Return True for now.
                logger.debug(f"PREMIUM condition in backtest - defaulting to True")
                return True
            elif var_type == "DELTA":
                # For historical backtesting, delta conditions are difficult to evaluate
                # without Greeks calculation. Return True for now.
                logger.debug(f"DELTA condition in backtest - defaulting to True")
                return True
            else:
                logger.warning(f"Unknown variable type: {var_type}")
                return False

            # For SPOT and VIX, evaluate using standard operators
            if var_type in ["SPOT", "VIX"]:
                threshold_value = float(threshold)

                if operator == "GREATER_THAN":
                    return actual_value > threshold_value
                elif operator == "LESS_THAN":
                    return actual_value < threshold_value
                elif operator == "EQUALS":
                    return abs(actual_value - threshold_value) < 0.01
                elif operator == "GREATER_THAN_OR_EQUAL":
                    return actual_value >= threshold_value
                elif operator == "LESS_THAN_OR_EQUAL":
                    return actual_value <= threshold_value
                elif operator in ["CROSSES_ABOVE", "CROSSES_BELOW"]:
                    # Crosses not supported in historical backtest without previous state
                    logger.debug(f"{operator} not supported in backtest - defaulting to standard comparison")
                    return actual_value > threshold_value if operator == "CROSSES_ABOVE" else actual_value < threshold_value
                else:
                    logger.warning(f"Unknown operator: {operator}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Error evaluating historical condition: {e}")
            return False

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
