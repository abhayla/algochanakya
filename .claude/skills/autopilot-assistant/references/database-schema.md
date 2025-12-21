# AutoPilot Database Schema

14 core tables for the AutoPilot system.

## Core Tables

### autopilot_user_settings

Global user settings (1:1 with users).

**Key Fields:**
- `daily_loss_limit` (Decimal) - Max loss per day
- `max_active_strategies` (Integer) - Concurrent strategy limit
- `kill_switch_enabled` (Boolean)
- `default_execution_mode` - "auto"|"semi_auto"|"manual"
- `delta_hedge_threshold` (Decimal) - Delta threshold for hedging
- `vega_hedge_threshold` (Decimal)

### autopilot_strategies

Strategy configurations and runtime state.

**Key Fields:**
- `name`, `status`, `underlying`, `expiry_type`, `lots`
- `legs_config` (JSONB) - Array of leg configurations
- `entry_conditions` (JSONB) - Entry condition logic
- `adjustment_rules` (JSONB) - Adjustment rules array
- `order_settings` (JSONB) - Order execution config
- `risk_settings` (JSONB) - Max loss, trailing stop
- `schedule_config` (JSONB) - Active days/times
- `trading_mode` - "live"|"paper"

**legs_config Structure:**
```json
[{
  "id": "leg_1",
  "contract_type": "CE|PE",
  "transaction_type": "BUY|SELL",
  "strike_selection": {
    "mode": "atm_offset|premium_based|delta_based|fixed",
    "offset": 0,
    "target_premium": 100.0,
    "target_delta": 0.30,
    "strike": 24500
  },
  "quantity_multiplier": 1
}]
```

**entry_conditions Structure:**
```json
{
  "logic": "AND|OR",
  "conditions": [{
    "id": "cond_1",
    "enabled": true,
    "variable": "TIME.CURRENT",
    "operator": "greater_equal",
    "value": "09:20"
  }]
}
```

### autopilot_orders

Order execution history with slippage tracking.

**Key Fields:**
- `kite_order_id`, `purpose` (entry/adjustment/exit)
- `tradingsymbol`, `quantity`, `order_type`, `status`
- `expected_price`, `executed_price`, `slippage`
- `delta`, `gamma`, `theta`, `vega` (at order time)

### autopilot_order_batches

Groups related orders (entry, adjustment, exit).

**Key Fields:**
- `purpose` - "entry"|"adjustment"|"exit"
- `total_orders`, `successful_orders`, `failed_orders`
- `market_snapshot` (JSONB) - Spot, VIX at execution
- `triggered_condition` (JSONB) - Which condition triggered

### autopilot_logs

Activity logs and events.

**Key Fields:**
- `event_type` - "entry"|"exit"|"adjustment"|"risk_alert"|"error"
- `severity` - "info"|"warning"|"error"
- `message`, `event_data` (JSONB)

### autopilot_condition_eval

Condition evaluation snapshots.

**Key Fields:**
- `condition_id`, `variable`, `operator`, `expected_value`, `current_value`
- `is_satisfied` (Boolean)
- `progress_pct` (Float) - How close to satisfaction

### autopilot_daily_summary

Daily P&L aggregates.

**Key Fields:**
- `strategies_run`, `total_realized_pnl`, `total_unrealized_pnl`
- `max_drawdown`, `win_rate`

### autopilot_templates

Pre-built strategy templates.

**Key Fields:**
- `name`, `category` - "bullish"|"bearish"|"neutral"
- `strategy_config` (JSONB) - Complete strategy configuration
- `risk_level` - "low"|"medium"|"high"
- `educational_content` (JSONB)

## Phase 5+ Tables

### autopilot_adjustment_logs

Adjustment rule execution history.

**Key Fields:**
- `trigger_type`, `action_type`, `executed` (Boolean)
- `confirmation_id` (for semi-auto)

### autopilot_pending_confirmations

Semi-auto confirmation requests.

**Key Fields:**
- `action_type`, `status` - "pending"|"confirmed"|"rejected"
- `expires_at`

### autopilot_position_legs

Individual leg tracking with Greeks.

**Key Fields:**
- `contract_type`, `strike`, `entry_price`, `current_price`
- `delta`, `gamma`, `theta`, `vega`
- `unrealized_pnl`

### autopilot_adjustment_suggestions

AI-generated adjustment suggestions.

**Key Fields:**
- `suggestion_type`, `urgency`, `confidence`
- `one_click_action` (JSONB)

### autopilot_trade_journal

Trade logging for analysis.

**Key Fields:**
- `legs` (JSONB), `gross_pnl`, `net_pnl`
- `exit_reason`, `market_conditions` (JSONB)

### autopilot_backtests

Backtest configurations and results.

**Key Fields:**
- `strategy_config` (JSONB), `win_rate`, `sharpe_ratio`
- `equity_curve` (JSONB)
