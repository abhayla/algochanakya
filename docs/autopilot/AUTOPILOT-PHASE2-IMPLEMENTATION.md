# AutoPilot Phase 2 - Claude Code Implementation Guide

## Overview

Phase 2 adds real-time monitoring, condition evaluation, and order execution to the AutoPilot system.

**Project:** AlgoChanakya  
**Feature:** AutoPilot - Real-time Monitoring & Execution  
**Phase:** 2 - WebSocket, Condition Engine, Order Execution  
**Duration:** 4-5 weeks  
**Prerequisites:** Phase 1 complete

---

## Phase 2 Scope

### What to Build

| Component | Priority | Description |
|-----------|----------|-------------|
| WebSocket Server | P0 | Real-time updates to frontend |
| WebSocket Client (Frontend) | P0 | Connect and receive updates |
| Condition Engine | P0 | Evaluate entry conditions |
| Market Data Service | P0 | Fetch LTP, VIX from Kite |
| Order Execution Service | P1 | Place orders via Kite Connect |
| Strategy Monitor | P1 | Background task to monitor strategies |
| Live P&L Calculator | P1 | Real-time P&L updates |
| Activity Feed API | P2 | Recent logs endpoint |
| Notification Service | P2 | In-app notifications |

### What NOT to Build in Phase 2

- Adjustment rules execution (Phase 3)
- Semi-auto confirmation flow (Phase 3)
- Kill switch (Phase 3)
- Templates marketplace (Phase 4)
- Backtest engine (Phase 4)
- Analytics dashboard (Phase 4)

---

## Documentation References

| Document | Location | Relevant Sections |
|----------|----------|-------------------|
| API Contracts | `docs/autopilot/api-contracts.md` | WebSocket API, Orders API |
| Component Design | `docs/autopilot/component-design.md` | Real-time components |
| Database Schema | `docs/autopilot/database-schema.md` | Orders, Logs, Condition Eval |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue.js 3)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ Dashboard   │  │ Strategy    │  │ Notifications│                 │
│  │ View        │  │ Detail      │  │ Component    │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          │                                          │
│                 ┌────────▼────────┐                                 │
│                 │  useWebSocket   │  (Composable)                   │
│                 │  Composable     │                                 │
│                 └────────┬────────┘                                 │
└──────────────────────────┼──────────────────────────────────────────┘
                           │ WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                             │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ WebSocket       │    │ Strategy        │    │ Order           │  │
│  │ Manager         │◄───│ Monitor         │───▶│ Executor        │  │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘  │
│           │                      │                      │           │
│           │              ┌───────▼───────┐              │           │
│           │              │ Condition     │              │           │
│           │              │ Engine        │              │           │
│           │              └───────┬───────┘              │           │
│           │                      │                      │           │
│           │              ┌───────▼───────┐              │           │
│           └──────────────│ Market Data   │──────────────┘           │
│                          │ Service       │                          │
│                          └───────┬───────┘                          │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Kite Connect   │
                          │  API            │
                          └─────────────────┘
```

---

## Implementation Tasks

### Task 1: Market Data Service

**File:** `backend/app/services/market_data.py`

```python
"""
Market Data Service

Fetches real-time market data from Kite Connect API.
Provides LTP, OHLC, VIX, and spot prices.
"""
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging

from kiteconnect import KiteConnect

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MarketQuote:
    """Market quote data."""
    instrument_token: int
    tradingsymbol: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: int
    timestamp: datetime


@dataclass
class SpotData:
    """Spot/Index data."""
    symbol: str
    ltp: Decimal
    change: Decimal
    change_pct: float
    timestamp: datetime


class MarketDataService:
    """Service for fetching market data from Kite Connect."""
    
    # Instrument tokens for indices
    INDEX_TOKENS = {
        "NIFTY": 256265,      # NIFTY 50
        "BANKNIFTY": 260105,  # BANK NIFTY
        "FINNIFTY": 257801,   # FIN NIFTY
        "SENSEX": 265,        # SENSEX (BSE)
        "INDIAVIX": 264969,   # INDIA VIX
    }
    
    def __init__(self, kite: KiteConnect):
        self.kite = kite
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = 1  # seconds
    
    async def get_ltp(self, instruments: List[str]) -> Dict[str, Decimal]:
        """
        Get Last Traded Price for instruments.
        
        Args:
            instruments: List of instrument identifiers (e.g., ["NFO:NIFTY24DEC24500CE"])
        
        Returns:
            Dict mapping instrument to LTP
        """
        try:
            # Kite API call (sync, wrap in executor)
            loop = asyncio.get_event_loop()
            ltp_data = await loop.run_in_executor(
                None, 
                self.kite.ltp, 
                instruments
            )
            
            result = {}
            for key, data in ltp_data.items():
                result[key] = Decimal(str(data['last_price']))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            raise
    
    async def get_quote(self, instruments: List[str]) -> Dict[str, MarketQuote]:
        """
        Get full quote for instruments.
        
        Args:
            instruments: List of instrument identifiers
        
        Returns:
            Dict mapping instrument to MarketQuote
        """
        try:
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                instruments
            )
            
            result = {}
            for key, data in quote_data.items():
                result[key] = MarketQuote(
                    instrument_token=data['instrument_token'],
                    tradingsymbol=data.get('tradingsymbol', key),
                    ltp=Decimal(str(data['last_price'])),
                    open=Decimal(str(data['ohlc']['open'])),
                    high=Decimal(str(data['ohlc']['high'])),
                    low=Decimal(str(data['ohlc']['low'])),
                    close=Decimal(str(data['ohlc']['close'])),
                    volume=data.get('volume', 0),
                    oi=data.get('oi', 0),
                    timestamp=datetime.now()
                )
            
            return result
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            raise
    
    async def get_spot_price(self, underlying: str) -> SpotData:
        """
        Get spot price for an underlying index.
        
        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY, SENSEX
        
        Returns:
            SpotData with current price and change
        """
        token = self.INDEX_TOKENS.get(underlying.upper())
        if not token:
            raise ValueError(f"Unknown underlying: {underlying}")
        
        # Check cache
        cache_key = f"spot_{underlying}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            instrument = f"NSE:{underlying}"
            if underlying == "SENSEX":
                instrument = f"BSE:{underlying}"
            
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                [instrument]
            )
            
            data = quote_data[instrument]
            spot = SpotData(
                symbol=underlying,
                ltp=Decimal(str(data['last_price'])),
                change=Decimal(str(data['net_change'])),
                change_pct=float(data['change']),
                timestamp=datetime.now()
            )
            
            # Cache result
            self._cache[cache_key] = spot
            self._cache_expiry[cache_key] = datetime.now()
            
            return spot
        except Exception as e:
            logger.error(f"Error fetching spot price for {underlying}: {e}")
            raise
    
    async def get_vix(self) -> Decimal:
        """
        Get current India VIX value.
        
        Returns:
            VIX value as Decimal
        """
        cache_key = "vix"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            quote_data = await loop.run_in_executor(
                None,
                self.kite.quote,
                ["NSE:INDIAVIX"]
            )
            
            vix = Decimal(str(quote_data["NSE:INDIAVIX"]['last_price']))
            
            # Cache result
            self._cache[cache_key] = vix
            self._cache_expiry[cache_key] = datetime.now()
            
            return vix
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
            raise
    
    async def get_option_chain_ltp(
        self, 
        underlying: str, 
        expiry: date, 
        strikes: List[Decimal]
    ) -> Dict[str, Decimal]:
        """
        Get LTP for multiple strikes in option chain.
        
        Args:
            underlying: NIFTY, BANKNIFTY, etc.
            expiry: Expiry date
            strikes: List of strike prices
        
        Returns:
            Dict mapping tradingsymbol to LTP
        """
        instruments = []
        expiry_str = expiry.strftime("%y%b%d").upper()  # e.g., "24DEC26"
        
        for strike in strikes:
            strike_int = int(strike)
            ce_symbol = f"NFO:{underlying}{expiry_str}{strike_int}CE"
            pe_symbol = f"NFO:{underlying}{expiry_str}{strike_int}PE"
            instruments.extend([ce_symbol, pe_symbol])
        
        return await self.get_ltp(instruments)
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache or key not in self._cache_expiry:
            return False
        
        elapsed = (datetime.now() - self._cache_expiry[key]).total_seconds()
        return elapsed < self._cache_ttl


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service(kite: KiteConnect) -> MarketDataService:
    """Get or create MarketDataService instance."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService(kite)
    return _market_data_service
```

---

### Task 2: Condition Engine

**File:** `backend/app/services/condition_engine.py`

```python
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

from app.services.market_data import MarketDataService, get_market_data_service

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
            
            return ConditionResult(
                condition_id=condition_id,
                variable=variable,
                operator=operator,
                target_value=target_value,
                current_value=current_value,
                is_met=is_met
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
            # Would need to calculate premium based on leg config
            # For now, return placeholder
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
                target = float(target)
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
    
    def _parse_time(self, time_str: str) -> int:
        """Parse time string to minutes since midnight."""
        if isinstance(time_str, int):
            return time_str
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])


# Singleton instance
_condition_engine: Optional[ConditionEngine] = None


def get_condition_engine(market_data: MarketDataService) -> ConditionEngine:
    """Get or create ConditionEngine instance."""
    global _condition_engine
    if _condition_engine is None:
        _condition_engine = ConditionEngine(market_data)
    return _condition_engine
```

---

### Task 3: Order Execution Service

**File:** `backend/app/services/order_executor.py`

```python
"""
Order Execution Service

Executes orders via Kite Connect API for AutoPilot strategies.
Handles order placement, modification, and cancellation.
"""
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.autopilot import AutoPilotStrategy, AutoPilotOrder, AutoPilotLog
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Order request details."""
    strategy_id: int
    leg_id: str
    leg_index: int
    purpose: str  # entry, exit, adjustment, hedge
    exchange: str
    tradingsymbol: str
    transaction_type: str  # BUY, SELL
    quantity: int
    order_type: str  # MARKET, LIMIT, SL, SL-M
    product: str  # NRML, MIS
    price: Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    underlying: str = ""
    contract_type: str = ""  # CE, PE, FUT
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None


@dataclass
class OrderResult:
    """Result of order placement."""
    success: bool
    order_id: Optional[str] = None
    kite_order_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    executed_price: Optional[Decimal] = None
    slippage: Optional[Decimal] = None


class OrderExecutor:
    """
    Executes orders via Kite Connect.
    
    Features:
    - Sequential and simultaneous execution
    - Slippage protection
    - Retry on failure
    - Order tracking
    """
    
    def __init__(self, kite: KiteConnect, market_data: MarketDataService):
        self.kite = kite
        self.market_data = market_data
    
    async def execute_entry(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        dry_run: bool = False
    ) -> Tuple[bool, List[OrderResult]]:
        """
        Execute entry orders for a strategy.
        
        Args:
            db: Database session
            strategy: Strategy to execute
            dry_run: If True, simulate without placing real orders
        
        Returns:
            Tuple of (success, list of order results)
        """
        legs_config = strategy.legs_config or []
        order_settings = strategy.order_settings or {}
        
        execution_style = order_settings.get('execution_style', 'sequential')
        leg_sequence = order_settings.get('leg_sequence', [])
        delay_between = order_settings.get('delay_between_legs', 2)
        
        # Sort legs by execution order
        if leg_sequence:
            sorted_legs = sorted(
                legs_config, 
                key=lambda x: leg_sequence.index(x['id']) if x['id'] in leg_sequence else 999
            )
        else:
            sorted_legs = sorted(legs_config, key=lambda x: x.get('execution_order', 1))
        
        results: List[OrderResult] = []
        all_success = True
        
        # Build order requests
        order_requests = await self._build_order_requests(
            strategy=strategy,
            legs=sorted_legs,
            purpose="entry"
        )
        
        if execution_style == 'simultaneous':
            # Execute all orders at once
            tasks = [
                self._place_order(db, req, strategy, dry_run)
                for req in order_requests
            ]
            results = await asyncio.gather(*tasks)
            all_success = all(r.success for r in results)
        else:
            # Execute sequentially with delay
            for i, req in enumerate(order_requests):
                result = await self._place_order(db, req, strategy, dry_run)
                results.append(result)
                
                if not result.success:
                    all_success = False
                    # Check on_leg_failure setting
                    on_failure = order_settings.get('on_leg_failure', 'stop')
                    if on_failure == 'stop':
                        logger.warning(f"Stopping execution due to leg failure: {result.error}")
                        break
                
                # Delay between legs
                if i < len(order_requests) - 1 and delay_between > 0:
                    await asyncio.sleep(delay_between)
        
        return all_success, results
    
    async def execute_exit(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        exit_type: str = "market",
        reason: str = "manual",
        dry_run: bool = False
    ) -> Tuple[bool, List[OrderResult]]:
        """
        Execute exit orders to close all positions.
        
        Args:
            db: Database session
            strategy: Strategy to exit
            exit_type: market, limit
            reason: Reason for exit
            dry_run: Simulate without real orders
        
        Returns:
            Tuple of (success, list of order results)
        """
        # Get current positions from runtime_state
        runtime_state = strategy.runtime_state or {}
        current_positions = runtime_state.get('current_positions', [])
        
        if not current_positions:
            logger.info(f"No positions to exit for strategy {strategy.id}")
            return True, []
        
        results: List[OrderResult] = []
        all_success = True
        
        for position in current_positions:
            # Create reverse order to close position
            req = OrderRequest(
                strategy_id=strategy.id,
                leg_id=position.get('leg_id', ''),
                leg_index=position.get('leg_index', 0),
                purpose="exit",
                exchange=position.get('exchange', 'NFO'),
                tradingsymbol=position.get('tradingsymbol'),
                transaction_type="SELL" if position.get('quantity', 0) > 0 else "BUY",
                quantity=abs(position.get('quantity', 0)),
                order_type="MARKET" if exit_type == "market" else "LIMIT",
                product=position.get('product', 'NRML'),
                underlying=strategy.underlying,
                contract_type=position.get('contract_type', ''),
                strike=position.get('strike'),
                expiry=position.get('expiry')
            )
            
            result = await self._place_order(db, req, strategy, dry_run)
            results.append(result)
            
            if not result.success:
                all_success = False
        
        return all_success, results
    
    async def _build_order_requests(
        self,
        strategy: AutoPilotStrategy,
        legs: List[Dict[str, Any]],
        purpose: str
    ) -> List[OrderRequest]:
        """Build order requests from leg configurations."""
        requests = []
        
        # Get spot price for strike selection
        spot_data = await self.market_data.get_spot_price(strategy.underlying)
        spot_price = float(spot_data.ltp)
        
        # Determine expiry
        expiry_date = strategy.expiry_date
        if not expiry_date:
            # Would need to calculate based on expiry_type
            # For now, use a placeholder
            expiry_date = date.today()
        
        lot_size = self._get_lot_size(strategy.underlying)
        
        for i, leg in enumerate(legs):
            strike = await self._calculate_strike(
                leg=leg,
                spot_price=spot_price,
                underlying=strategy.underlying
            )
            
            tradingsymbol = self._build_tradingsymbol(
                underlying=strategy.underlying,
                expiry=expiry_date,
                strike=strike,
                contract_type=leg['contract_type']
            )
            
            quantity = strategy.lots * lot_size * leg.get('quantity_multiplier', 1)
            
            req = OrderRequest(
                strategy_id=strategy.id,
                leg_id=leg['id'],
                leg_index=i,
                purpose=purpose,
                exchange="NFO",
                tradingsymbol=tradingsymbol,
                transaction_type=leg['transaction_type'],
                quantity=quantity,
                order_type=strategy.order_settings.get('order_type', 'MARKET'),
                product="NRML" if strategy.position_type == "positional" else "MIS",
                underlying=strategy.underlying,
                contract_type=leg['contract_type'],
                strike=Decimal(str(strike)),
                expiry=expiry_date
            )
            requests.append(req)
        
        return requests
    
    async def _place_order(
        self,
        db: AsyncSession,
        request: OrderRequest,
        strategy: AutoPilotStrategy,
        dry_run: bool
    ) -> OrderResult:
        """Place a single order."""
        
        # Get LTP before order
        try:
            instrument_key = f"NFO:{request.tradingsymbol}"
            ltp_data = await self.market_data.get_ltp([instrument_key])
            ltp_at_order = ltp_data.get(instrument_key)
        except:
            ltp_at_order = None
        
        if dry_run:
            # Simulate order
            logger.info(f"[DRY RUN] Would place order: {request}")
            return OrderResult(
                success=True,
                order_id=f"dry_run_{request.leg_id}",
                kite_order_id=None,
                message="Dry run - order simulated",
                executed_price=ltp_at_order
            )
        
        try:
            # Place order via Kite
            loop = asyncio.get_event_loop()
            order_params = {
                "exchange": request.exchange,
                "tradingsymbol": request.tradingsymbol,
                "transaction_type": request.transaction_type,
                "quantity": request.quantity,
                "order_type": request.order_type,
                "product": request.product,
            }
            
            if request.price:
                order_params["price"] = float(request.price)
            if request.trigger_price:
                order_params["trigger_price"] = float(request.trigger_price)
            
            kite_order_id = await loop.run_in_executor(
                None,
                lambda: self.kite.place_order(variety="regular", **order_params)
            )
            
            # Create order record in database
            order = AutoPilotOrder(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                kite_order_id=str(kite_order_id),
                purpose=request.purpose,
                leg_index=request.leg_index,
                exchange=request.exchange,
                tradingsymbol=request.tradingsymbol,
                underlying=request.underlying,
                contract_type=request.contract_type,
                strike=request.strike,
                expiry=request.expiry,
                transaction_type=request.transaction_type,
                order_type=request.order_type,
                product=request.product,
                quantity=request.quantity,
                ltp_at_order=ltp_at_order,
                status="placed",
                order_placed_at=datetime.now()
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)
            
            # Log the order
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                order_id=order.id,
                event_type="order_placed",
                severity="info",
                message=f"Order placed: {request.transaction_type} {request.quantity} {request.tradingsymbol}",
                event_data={
                    "kite_order_id": kite_order_id,
                    "leg_id": request.leg_id,
                    "purpose": request.purpose
                }
            )
            db.add(log)
            await db.commit()
            
            return OrderResult(
                success=True,
                order_id=str(order.id),
                kite_order_id=str(kite_order_id),
                message="Order placed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            
            # Log the error
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="order_error",
                severity="error",
                message=f"Order failed: {str(e)}",
                event_data={
                    "leg_id": request.leg_id,
                    "error": str(e)
                }
            )
            db.add(log)
            await db.commit()
            
            return OrderResult(
                success=False,
                error=str(e),
                message=f"Order failed: {str(e)}"
            )
    
    async def _calculate_strike(
        self,
        leg: Dict[str, Any],
        spot_price: float,
        underlying: str
    ) -> float:
        """Calculate strike price based on leg configuration."""
        strike_selection = leg.get('strike_selection', {})
        mode = strike_selection.get('mode', 'atm_offset')
        
        # Get strike step
        strike_step = self._get_strike_step(underlying)
        
        # Calculate ATM strike
        atm_strike = round(spot_price / strike_step) * strike_step
        
        if mode == 'fixed':
            return strike_selection.get('fixed_strike', atm_strike)
        
        elif mode == 'atm_offset':
            offset = strike_selection.get('offset', 0)
            return atm_strike + offset
        
        elif mode == 'premium_based':
            # Would need to search for strike with target premium
            # For now, return ATM
            return atm_strike
        
        elif mode == 'delta_based':
            # Would need option chain with Greeks
            # For now, return ATM
            return atm_strike
        
        return atm_strike
    
    def _build_tradingsymbol(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        contract_type: str
    ) -> str:
        """Build Kite tradingsymbol."""
        expiry_str = expiry.strftime("%y%b").upper()  # e.g., "24DEC"
        day = expiry.strftime("%d")
        
        # Weekly expiry format: NIFTY24D2624500CE
        # Monthly expiry format: NIFTY24DEC24500CE
        if expiry.day <= 7:
            # Likely weekly
            expiry_str = expiry.strftime("%y%b%d").upper()
        
        return f"{underlying}{expiry_str}{int(strike)}{contract_type}"
    
    def _get_lot_size(self, underlying: str) -> int:
        """Get lot size for underlying."""
        lot_sizes = {
            "NIFTY": 25,
            "BANKNIFTY": 15,
            "FINNIFTY": 25,
            "SENSEX": 10,
        }
        return lot_sizes.get(underlying.upper(), 25)
    
    def _get_strike_step(self, underlying: str) -> float:
        """Get strike step for underlying."""
        strike_steps = {
            "NIFTY": 50,
            "BANKNIFTY": 100,
            "FINNIFTY": 50,
            "SENSEX": 100,
        }
        return strike_steps.get(underlying.upper(), 50)
```

---

### Task 4: WebSocket Manager (Backend)

**File:** `backend/app/websocket/manager.py`

```python
"""
WebSocket Manager

Manages WebSocket connections for real-time updates.
Broadcasts strategy updates, P&L changes, and notifications.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    # Connection
    CONNECTED = "connected"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    
    # Strategy updates
    STRATEGY_UPDATE = "strategy_update"
    STRATEGY_STATUS_CHANGED = "strategy_status_changed"
    
    # Order updates
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    
    # P&L updates
    PNL_UPDATE = "pnl_update"
    
    # Condition updates
    CONDITION_EVALUATED = "condition_evaluated"
    CONDITIONS_MET = "conditions_met"
    
    # Risk alerts
    RISK_ALERT = "risk_alert"
    DAILY_LIMIT_WARNING = "daily_limit_warning"
    
    # System
    MARKET_STATUS = "market_status"
    HEARTBEAT = "heartbeat"


@dataclass
class WSMessage:
    """WebSocket message structure."""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp
        })


class ConnectionManager:
    """
    Manages WebSocket connections.
    
    Features:
    - Per-user connection tracking
    - Broadcast to all users
    - Broadcast to specific user
    - Heartbeat mechanism
    - Auto-reconnection handling
    """
    
    def __init__(self):
        # user_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user_id mapping
        self._ws_to_user: Dict[WebSocket, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        
        Returns:
            True if connection successful
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                if user_id not in self._connections:
                    self._connections[user_id] = set()
                self._connections[user_id].add(websocket)
                self._ws_to_user[websocket] = user_id
            
            logger.info(f"WebSocket connected for user {user_id}")
            
            # Send connected message
            await self.send_to_connection(
                websocket,
                WSMessage(
                    type=MessageType.CONNECTED,
                    data={"user_id": user_id, "message": "Connected to AutoPilot"}
                )
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            return False
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            user_id = self._ws_to_user.pop(websocket, None)
            if user_id and user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: WSMessage):
        """Send message to all connections of a specific user."""
        async with self._lock:
            connections = self._connections.get(user_id, set()).copy()
        
        for websocket in connections:
            await self.send_to_connection(websocket, message)
    
    async def send_to_connection(self, websocket: WebSocket, message: WSMessage):
        """Send message to a specific WebSocket connection."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: WSMessage, user_ids: Optional[List[str]] = None):
        """
        Broadcast message to multiple users.
        
        Args:
            message: Message to broadcast
            user_ids: List of user IDs. If None, broadcast to all.
        """
        async with self._lock:
            if user_ids is None:
                targets = list(self._connections.keys())
            else:
                targets = user_ids
        
        for user_id in targets:
            await self.send_to_user(user_id, message)
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs."""
        return list(self._connections.keys())
    
    def get_connection_count(self, user_id: str) -> int:
        """Get number of connections for a user."""
        return len(self._connections.get(user_id, set()))
    
    # ========================================================================
    # Convenience methods for specific message types
    # ========================================================================
    
    async def send_strategy_update(
        self,
        user_id: str,
        strategy_id: int,
        updates: Dict[str, Any]
    ):
        """Send strategy update to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.STRATEGY_UPDATE,
                data={"strategy_id": strategy_id, **updates}
            )
        )
    
    async def send_status_change(
        self,
        user_id: str,
        strategy_id: int,
        old_status: str,
        new_status: str,
        reason: str = ""
    ):
        """Send strategy status change notification."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.STRATEGY_STATUS_CHANGED,
                data={
                    "strategy_id": strategy_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason
                }
            )
        )
    
    async def send_order_update(
        self,
        user_id: str,
        strategy_id: int,
        order_id: int,
        event_type: MessageType,
        order_data: Dict[str, Any]
    ):
        """Send order event notification."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=event_type,
                data={
                    "strategy_id": strategy_id,
                    "order_id": order_id,
                    **order_data
                }
            )
        )
    
    async def send_pnl_update(
        self,
        user_id: str,
        strategy_id: int,
        realized_pnl: float,
        unrealized_pnl: float,
        total_pnl: float
    ):
        """Send P&L update to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.PNL_UPDATE,
                data={
                    "strategy_id": strategy_id,
                    "realized_pnl": realized_pnl,
                    "unrealized_pnl": unrealized_pnl,
                    "total_pnl": total_pnl
                }
            )
        )
    
    async def send_condition_update(
        self,
        user_id: str,
        strategy_id: int,
        conditions_met: bool,
        condition_states: List[Dict[str, Any]]
    ):
        """Send condition evaluation update."""
        msg_type = MessageType.CONDITIONS_MET if conditions_met else MessageType.CONDITION_EVALUATED
        await self.send_to_user(
            user_id,
            WSMessage(
                type=msg_type,
                data={
                    "strategy_id": strategy_id,
                    "conditions_met": conditions_met,
                    "condition_states": condition_states
                }
            )
        )
    
    async def send_risk_alert(
        self,
        user_id: str,
        alert_type: str,
        message: str,
        data: Dict[str, Any]
    ):
        """Send risk alert to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.RISK_ALERT,
                data={
                    "alert_type": alert_type,
                    "message": message,
                    **data
                }
            )
        )


# Singleton instance
ws_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """Get WebSocket manager instance."""
    return ws_manager
```

---

### Task 5: WebSocket Endpoint

**File:** `backend/app/websocket/routes.py`

```python
"""
WebSocket Routes

WebSocket endpoint for AutoPilot real-time updates.
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt, JWTError

from app.config import settings
from app.websocket.manager import get_ws_manager, WSMessage, MessageType

router = APIRouter()


async def get_user_from_token(token: str) -> str:
    """Validate JWT token and return user ID."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token")
        return str(user_id)
    except JWTError as e:
        raise ValueError(f"Token validation failed: {e}")


@router.websocket("/ws/autopilot")
async def autopilot_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for AutoPilot real-time updates.
    
    Connect with: ws://host/ws/autopilot?token=<jwt_token>
    
    Messages received:
    - ping: Respond with pong
    - subscribe: Subscribe to specific strategy updates
    - unsubscribe: Unsubscribe from strategy updates
    
    Messages sent:
    - connected: Connection established
    - pong: Response to ping
    - strategy_update: Strategy data changed
    - strategy_status_changed: Status transition
    - order_placed/filled/rejected: Order events
    - pnl_update: P&L changes
    - condition_evaluated: Condition check results
    - conditions_met: All conditions satisfied
    - risk_alert: Risk limit warnings
    """
    manager = get_ws_manager()
    
    # Validate token
    try:
        user_id = await get_user_from_token(token)
    except ValueError as e:
        await websocket.close(code=4001, reason=str(e))
        return
    
    # Connect
    connected = await manager.connect(websocket, user_id)
    if not connected:
        return
    
    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(websocket, manager)
        )
        
        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type", "")
                
                if msg_type == "ping":
                    await manager.send_to_connection(
                        websocket,
                        WSMessage(type=MessageType.PONG, data={})
                    )
                
                elif msg_type == "subscribe":
                    # Handle subscription to specific strategy
                    strategy_id = message.get("data", {}).get("strategy_id")
                    if strategy_id:
                        # Store subscription (could use Redis for scaling)
                        pass
                
                elif msg_type == "unsubscribe":
                    # Handle unsubscription
                    strategy_id = message.get("data", {}).get("strategy_id")
                    if strategy_id:
                        pass
                
            except json.JSONDecodeError:
                await manager.send_to_connection(
                    websocket,
                    WSMessage(
                        type=MessageType.ERROR,
                        data={"message": "Invalid JSON"}
                    )
                )
                
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(websocket)


async def _heartbeat_loop(websocket: WebSocket, manager):
    """Send periodic heartbeat to keep connection alive."""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        try:
            await manager.send_to_connection(
                websocket,
                WSMessage(type=MessageType.HEARTBEAT, data={})
            )
        except:
            break
```

**Register WebSocket route in main.py:**

```python
# Add to backend/app/main.py
from app.websocket.routes import router as ws_router

app.include_router(ws_router)
```

---

### Task 6: Strategy Monitor (Background Task)

**File:** `backend/app/services/strategy_monitor.py`

```python
"""
Strategy Monitor

Background service that monitors active strategies.
Evaluates conditions and triggers order execution.
"""
import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from kiteconnect import KiteConnect

from app.database import get_db_session
from app.models.autopilot import AutoPilotStrategy, AutoPilotUserSettings, AutoPilotLog
from app.services.market_data import MarketDataService, get_market_data_service
from app.services.condition_engine import ConditionEngine, get_condition_engine
from app.services.order_executor import OrderExecutor
from app.websocket.manager import get_ws_manager

logger = logging.getLogger(__name__)


class StrategyMonitor:
    """
    Monitors active AutoPilot strategies.
    
    Responsibilities:
    - Poll for waiting/active strategies
    - Evaluate entry conditions
    - Trigger order execution when conditions met
    - Update strategy status
    - Send WebSocket updates
    """
    
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    POLL_INTERVAL = 5  # seconds
    
    def __init__(
        self,
        kite: KiteConnect,
        market_data: MarketDataService,
        condition_engine: ConditionEngine
    ):
        self.kite = kite
        self.market_data = market_data
        self.condition_engine = condition_engine
        self.order_executor = OrderExecutor(kite, market_data)
        self.ws_manager = get_ws_manager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
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
        now = datetime.now().time()
        # Also check for weekday (Mon=0, Fri=4)
        weekday = datetime.now().weekday()
        if weekday > 4:  # Weekend
            return False
        return self.MARKET_OPEN <= now <= self.MARKET_CLOSE
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                if self.is_market_open():
                    await self._process_strategies()
                else:
                    logger.debug("Market closed, skipping monitoring")
                
                await asyncio.sleep(self.POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.POLL_INTERVAL)
    
    async def _process_strategies(self):
        """Process all active strategies."""
        async with get_db_session() as db:
            # Get all waiting strategies
            result = await db.execute(
                select(AutoPilotStrategy).where(
                    AutoPilotStrategy.status.in_(["waiting", "active"])
                )
            )
            strategies = result.scalars().all()
            
            for strategy in strategies:
                try:
                    await self._process_strategy(db, strategy)
                except Exception as e:
                    logger.error(f"Error processing strategy {strategy.id}: {e}")
    
    async def _process_strategy(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Process a single strategy."""
        
        # Check schedule
        if not self._is_schedule_active(strategy):
            return
        
        # Check user risk limits
        if not await self._check_risk_limits(db, strategy):
            return
        
        if strategy.status == "waiting":
            # Evaluate entry conditions
            await self._evaluate_and_execute(db, strategy)
        
        elif strategy.status == "active":
            # Update P&L
            await self._update_pnl(db, strategy)
            
            # Check risk-based exits
            await self._check_risk_exits(db, strategy)
    
    async def _evaluate_and_execute(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Evaluate conditions and execute if met."""
        
        # Evaluate conditions
        eval_result = await self.condition_engine.evaluate(
            strategy_id=strategy.id,
            entry_conditions=strategy.entry_conditions or {},
            underlying=strategy.underlying,
            legs_config=strategy.legs_config or []
        )
        
        # Send condition update via WebSocket
        await self.ws_manager.send_condition_update(
            user_id=str(strategy.user_id),
            strategy_id=strategy.id,
            conditions_met=eval_result.all_conditions_met,
            condition_states=[
                {
                    "condition_id": r.condition_id,
                    "variable": r.variable,
                    "current_value": r.current_value,
                    "target_value": r.target_value,
                    "is_met": r.is_met
                }
                for r in eval_result.individual_results
            ]
        )
        
        if eval_result.all_conditions_met:
            logger.info(f"Conditions met for strategy {strategy.id}, executing entry")
            
            # Check if paper trading
            paper_trading = (strategy.runtime_state or {}).get('paper_trading', False)
            
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
                
                # Update runtime state with positions
                runtime_state = strategy.runtime_state or {}
                runtime_state['entry_time'] = datetime.now().isoformat()
                runtime_state['entry_results'] = [
                    {"order_id": r.order_id, "success": r.success}
                    for r in results
                ]
                strategy.runtime_state = runtime_state
                
                await db.commit()
                
                # Send status change notification
                await self.ws_manager.send_status_change(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    old_status=old_status,
                    new_status="active",
                    reason="Entry conditions met"
                )
            else:
                # Handle execution failure
                strategy.status = "error"
                runtime_state = strategy.runtime_state or {}
                runtime_state['error'] = "Entry execution failed"
                strategy.runtime_state = runtime_state
                await db.commit()
                
                await self.ws_manager.send_status_change(
                    user_id=str(strategy.user_id),
                    strategy_id=strategy.id,
                    old_status="waiting",
                    new_status="error",
                    reason="Entry execution failed"
                )
    
    async def _update_pnl(self, db: AsyncSession, strategy: AutoPilotStrategy):
        """Update P&L for active strategy."""
        runtime_state = strategy.runtime_state or {}
        current_positions = runtime_state.get('current_positions', [])
        
        if not current_positions:
            return
        
        # Get current LTPs
        instruments = [f"NFO:{p['tradingsymbol']}" for p in current_positions]
        try:
            ltp_data = await self.market_data.get_ltp(instruments)
        except:
            return
        
        total_pnl = 0
        for position in current_positions:
            key = f"NFO:{position['tradingsymbol']}"
            current_ltp = float(ltp_data.get(key, 0))
            entry_price = float(position.get('entry_price', 0))
            quantity = position.get('quantity', 0)
            
            # Calculate P&L (positive qty = long, negative = short)
            pnl = (current_ltp - entry_price) * quantity
            total_pnl += pnl
        
        # Update runtime state
        runtime_state['current_pnl'] = total_pnl
        runtime_state['pnl_updated_at'] = datetime.now().isoformat()
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
            strategy.runtime_state = runtime_state
            await db.commit()
            
            await self.ws_manager.send_status_change(
                user_id=str(strategy.user_id),
                strategy_id=strategy.id,
                old_status=old_status,
                new_status="completed",
                reason=exit_reason
            )
    
    async def _check_risk_limits(self, db: AsyncSession, strategy: AutoPilotStrategy) -> bool:
        """Check if user's risk limits allow execution."""
        result = await db.execute(
            select(AutoPilotUserSettings).where(
                AutoPilotUserSettings.user_id == strategy.user_id
            )
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            return True  # No limits set
        
        # TODO: Check daily loss limit, capital limits, etc.
        
        return True
    
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
        
        return True


# Singleton instance
_strategy_monitor: Optional[StrategyMonitor] = None


async def get_strategy_monitor(kite: KiteConnect) -> StrategyMonitor:
    """Get or create StrategyMonitor instance."""
    global _strategy_monitor
    if _strategy_monitor is None:
        market_data = get_market_data_service(kite)
        condition_engine = get_condition_engine(market_data)
        _strategy_monitor = StrategyMonitor(kite, market_data, condition_engine)
    return _strategy_monitor
```

---

### Task 7: Frontend WebSocket Composable

**File:** `frontend/src/composables/autopilot/useWebSocket.js`

```javascript
/**
 * WebSocket Composable for AutoPilot
 * 
 * Manages WebSocket connection for real-time updates.
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAutopilotStore } from '@/stores/autopilot'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket() {
  const authStore = useAuthStore()
  const autopilotStore = useAutopilotStore()
  
  const socket = ref(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000
  
  let reconnectTimer = null
  let pingInterval = null
  
  const connectionStatus = computed(() => {
    if (isConnected.value) return 'connected'
    if (reconnectAttempts.value > 0) return 'reconnecting'
    return 'disconnected'
  })
  
  /**
   * Connect to WebSocket server
   */
  function connect() {
    if (socket.value?.readyState === WebSocket.OPEN) {
      return
    }
    
    const token = authStore.token
    if (!token) {
      console.warn('No auth token, cannot connect to WebSocket')
      return
    }
    
    const wsUrl = `${WS_URL}/ws/autopilot?token=${token}`
    
    try {
      socket.value = new WebSocket(wsUrl)
      
      socket.value.onopen = handleOpen
      socket.value.onclose = handleClose
      socket.value.onerror = handleError
      socket.value.onmessage = handleMessage
      
    } catch (error) {
      console.error('WebSocket connection error:', error)
      scheduleReconnect()
    }
  }
  
  /**
   * Disconnect from WebSocket server
   */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
    
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
    
    isConnected.value = false
    reconnectAttempts.value = 0
  }
  
  /**
   * Send message to server
   */
  function send(type, data = {}) {
    if (socket.value?.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify({ type, data }))
    }
  }
  
  /**
   * Subscribe to strategy updates
   */
  function subscribeToStrategy(strategyId) {
    send('subscribe', { strategy_id: strategyId })
  }
  
  /**
   * Unsubscribe from strategy updates
   */
  function unsubscribeFromStrategy(strategyId) {
    send('unsubscribe', { strategy_id: strategyId })
  }
  
  // ========================================================================
  // Event Handlers
  // ========================================================================
  
  function handleOpen() {
    console.log('WebSocket connected')
    isConnected.value = true
    reconnectAttempts.value = 0
    
    // Start ping interval
    pingInterval = setInterval(() => {
      send('ping')
    }, 25000)
  }
  
  function handleClose(event) {
    console.log('WebSocket closed:', event.code, event.reason)
    isConnected.value = false
    
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
    
    // Reconnect if not intentional close
    if (event.code !== 1000) {
      scheduleReconnect()
    }
  }
  
  function handleError(error) {
    console.error('WebSocket error:', error)
  }
  
  function handleMessage(event) {
    try {
      const message = JSON.parse(event.data)
      const { type, data, timestamp } = message
      
      switch (type) {
        case 'connected':
          console.log('WebSocket connected:', data.message)
          break
        
        case 'pong':
          // Heartbeat response
          break
        
        case 'heartbeat':
          // Server heartbeat
          break
        
        case 'strategy_update':
          handleStrategyUpdate(data)
          break
        
        case 'strategy_status_changed':
          handleStatusChange(data)
          break
        
        case 'order_placed':
        case 'order_filled':
        case 'order_rejected':
          handleOrderEvent(type, data)
          break
        
        case 'pnl_update':
          handlePnLUpdate(data)
          break
        
        case 'condition_evaluated':
        case 'conditions_met':
          handleConditionUpdate(data)
          break
        
        case 'risk_alert':
          handleRiskAlert(data)
          break
        
        default:
          console.log('Unknown message type:', type, data)
      }
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }
  
  // ========================================================================
  // Message Handlers
  // ========================================================================
  
  function handleStrategyUpdate(data) {
    const { strategy_id, ...updates } = data
    autopilotStore.updateStrategyInList(strategy_id, updates)
  }
  
  function handleStatusChange(data) {
    const { strategy_id, old_status, new_status, reason } = data
    
    // Update strategy in store
    autopilotStore.updateStrategyInList(strategy_id, { status: new_status })
    
    // Show notification
    showNotification(
      `Strategy status changed`,
      `${old_status} → ${new_status}${reason ? `: ${reason}` : ''}`,
      new_status === 'error' ? 'error' : 'info'
    )
    
    // Refresh dashboard
    autopilotStore.fetchDashboardSummary()
  }
  
  function handleOrderEvent(eventType, data) {
    const { strategy_id, order_id, ...orderData } = data
    
    let title, message, type
    
    switch (eventType) {
      case 'order_placed':
        title = 'Order Placed'
        message = `${orderData.transaction_type} ${orderData.quantity} ${orderData.tradingsymbol}`
        type = 'info'
        break
      
      case 'order_filled':
        title = 'Order Filled'
        message = `${orderData.tradingsymbol} @ ${orderData.executed_price}`
        type = 'success'
        break
      
      case 'order_rejected':
        title = 'Order Rejected'
        message = orderData.rejection_reason || 'Unknown reason'
        type = 'error'
        break
    }
    
    showNotification(title, message, type)
  }
  
  function handlePnLUpdate(data) {
    const { strategy_id, realized_pnl, unrealized_pnl, total_pnl } = data
    
    autopilotStore.updateStrategyInList(strategy_id, {
      current_pnl: total_pnl,
      runtime_state: {
        realized_pnl,
        unrealized_pnl,
        current_pnl: total_pnl
      }
    })
  }
  
  function handleConditionUpdate(data) {
    const { strategy_id, conditions_met, condition_states } = data
    
    // Update condition states in store
    if (autopilotStore.currentStrategy?.id === strategy_id) {
      autopilotStore.updateBuilderStrategy({
        _conditionStates: condition_states,
        _conditionsMet: conditions_met
      })
    }
    
    if (conditions_met) {
      showNotification(
        'Conditions Met!',
        `Strategy conditions satisfied, executing entry...`,
        'success'
      )
    }
  }
  
  function handleRiskAlert(data) {
    const { alert_type, message } = data
    showNotification('Risk Alert', message, 'warning')
  }
  
  // ========================================================================
  // Helpers
  // ========================================================================
  
  function scheduleReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.log('Max reconnect attempts reached')
      return
    }
    
    reconnectAttempts.value++
    const delay = reconnectDelay * reconnectAttempts.value
    
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})`)
    
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }
  
  function showNotification(title, message, type = 'info') {
    // Use your notification system (toast, etc.)
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`)
    
    // Example: emit event for notification component
    window.dispatchEvent(new CustomEvent('autopilot-notification', {
      detail: { title, message, type }
    }))
  }
  
  // ========================================================================
  // Lifecycle
  // ========================================================================
  
  onMounted(() => {
    if (authStore.isAuthenticated) {
      connect()
    }
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    // State
    isConnected,
    connectionStatus,
    reconnectAttempts,
    
    // Methods
    connect,
    disconnect,
    send,
    subscribeToStrategy,
    unsubscribeFromStrategy
  }
}
```

---

### Task 8: Update Dashboard View with Real-time

**File:** Update `frontend/src/views/autopilot/DashboardView.vue`

Add WebSocket integration to existing Dashboard:

```vue
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import { useWebSocket } from '@/composables/autopilot/useWebSocket'

const router = useRouter()
const store = useAutopilotStore()

// WebSocket connection
const { isConnected, connectionStatus, connect } = useWebSocket()

// ... rest of existing code ...

// Add connection status indicator in template
</script>

<template>
  <div class="p-6">
    <!-- Header with connection status -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">AutoPilot Dashboard</h1>
        <div class="flex items-center gap-2 mt-1">
          <span 
            class="h-2 w-2 rounded-full"
            :class="{
              'bg-green-500': connectionStatus === 'connected',
              'bg-yellow-500 animate-pulse': connectionStatus === 'reconnecting',
              'bg-red-500': connectionStatus === 'disconnected'
            }"
          ></span>
          <span class="text-sm text-gray-500">
            {{ connectionStatus === 'connected' ? 'Live' : connectionStatus }}
          </span>
        </div>
      </div>
      <!-- ... rest of header ... -->
    </div>
    
    <!-- ... rest of template ... -->
  </div>
</template>
```

---

## Phase 2 Completion Checklist

### Backend ✓
- [ ] Market Data Service (`app/services/market_data.py`)
- [ ] Condition Engine (`app/services/condition_engine.py`)
- [ ] Order Executor (`app/services/order_executor.py`)
- [ ] WebSocket Manager (`app/websocket/manager.py`)
- [ ] WebSocket Route (`app/websocket/routes.py`)
- [ ] Strategy Monitor (`app/services/strategy_monitor.py`)
- [ ] Register WebSocket route in `main.py`
- [ ] Start monitor on app startup

### Frontend ✓
- [ ] WebSocket Composable (`composables/autopilot/useWebSocket.js`)
- [ ] Update Dashboard with real-time connection
- [ ] Add notification system for WebSocket events
- [ ] Update Strategy Detail with live P&L

### Testing ✓
- [ ] Test WebSocket connection
- [ ] Test condition evaluation
- [ ] Test order execution (paper trading mode)
- [ ] Test P&L updates

---

## Environment Variables

Add to `backend/.env`:

```env
# Kite Connect
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret

# WebSocket
WS_HEARTBEAT_INTERVAL=30
```

Add to `frontend/.env`:

```env
VITE_WS_URL=ws://localhost:8000
```

---

## Success Criteria

Phase 2 is complete when:

1. ✅ WebSocket connects and shows "Live" status
2. ✅ Conditions evaluate in real-time
3. ✅ Orders execute when conditions met (paper trading)
4. ✅ P&L updates in real-time
5. ✅ Status changes trigger notifications
6. ✅ Strategy monitor runs in background

---

**Start with Task 1 (Market Data Service) and proceed sequentially.**
