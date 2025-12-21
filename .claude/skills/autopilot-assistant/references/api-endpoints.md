# AutoPilot API Endpoints Reference

Complete endpoint documentation for AutoPilot system.

**Base URL:** `/api/v1/autopilot/`

---

## Endpoint Map

```
/api/v1/autopilot/
│
├── strategies/
│   ├── GET     /                           # List strategies
│   ├── POST    /                           # Create strategy
│   ├── GET     /{id}                       # Get strategy
│   ├── PUT     /{id}                       # Update strategy
│   ├── DELETE  /{id}                       # Delete strategy
│   ├── POST    /{id}/activate              # Activate strategy
│   ├── POST    /{id}/pause                 # Pause strategy
│   ├── POST    /{id}/resume                # Resume strategy
│   ├── POST    /{id}/exit                  # Force exit
│   ├── POST    /{id}/clone                 # Clone strategy
│   ├── GET     /{id}/conditions            # Get condition states
│   └── POST    /{id}/backtest              # Run backtest
│
├── dashboard/
│   ├── GET     /summary                    # Dashboard summary
│   ├── GET     /activity                   # Activity feed
│   ├── GET     /risk                       # Risk metrics
│   └── GET     /performance                # Performance stats
│
├── orders/
│   ├── GET     /                           # List orders
│   ├── GET     /{id}                       # Get order details
│   └── GET     /export                     # Export orders CSV
│
├── logs/
│   ├── GET     /                           # List logs
│   ├── GET     /{id}                       # Get log details
│   └── GET     /export                     # Export logs CSV
│
├── settings/
│   ├── GET     /                           # Get settings
│   └── PUT     /                           # Update settings
│
├── templates/
│   ├── GET     /                           # List templates
│   ├── POST    /                           # Create template
│   ├── GET     /{id}                       # Get template
│   ├── PUT     /{id}                       # Update template
│   └── DELETE  /{id}                       # Delete template
│
├── kill-switch/
│   └── POST    /                           # Emergency stop
│
└── ws/
    └── WS      /stream                     # WebSocket connection
```

---

## Strategy Endpoints

### GET /strategies/

List all strategies with optional filters.

**Query Parameters:**
- `status` (optional) - Filter by status (draft, waiting, active, paused, completed)
- `underlying` (optional) - Filter by underlying (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)
- `page` (default: 1) - Page number
- `page_size` (default: 20, max: 100) - Items per page
- `sort_by` (default: "created_at") - Sort field
- `sort_order` (default: "desc") - asc or desc

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Iron Condor Auto",
      "status": "active",
      "underlying": "NIFTY",
      "lots": 2,
      "position_type": "intraday",
      "leg_count": 4,
      "current_pnl": 1250.00,
      "margin_used": 45000.00,
      "priority": 100,
      "created_at": "2025-12-20T10:30:00",
      "activated_at": "2025-12-21T09:20:00"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "has_next": false,
  "has_prev": false
}
```

---

### POST /strategies/

Create a new strategy in draft status.

**Request Body:**
```json
{
  "name": "Iron Condor Auto",
  "description": "Automated Iron Condor on NIFTY",
  "underlying": "NIFTY",
  "expiry_type": "current_week",
  "lots": 2,
  "position_type": "intraday",
  "legs_config": [
    {
      "id": "leg_1",
      "contract_type": "CE",
      "transaction_type": "SELL",
      "strike_selection": {
        "mode": "atm_offset",
        "offset": 2
      },
      "quantity_multiplier": 1
    },
    {
      "id": "leg_2",
      "contract_type": "CE",
      "transaction_type": "BUY",
      "strike_selection": {
        "mode": "atm_offset",
        "offset": 4
      },
      "quantity_multiplier": 1
    },
    {
      "id": "leg_3",
      "contract_type": "PE",
      "transaction_type": "SELL",
      "strike_selection": {
        "mode": "atm_offset",
        "offset": -2
      },
      "quantity_multiplier": 1
    },
    {
      "id": "leg_4",
      "contract_type": "PE",
      "transaction_type": "BUY",
      "strike_selection": {
        "mode": "atm_offset",
        "offset": -4
      },
      "quantity_multiplier": 1
    }
  ],
  "entry_conditions": {
    "logic": "AND",
    "conditions": [
      {
        "id": "cond_1",
        "enabled": true,
        "variable": "TIME.CURRENT",
        "operator": "greater_equal",
        "value": "09:20"
      },
      {
        "id": "cond_2",
        "enabled": true,
        "variable": "VIX.VALUE",
        "operator": "less_than",
        "value": 20.0
      }
    ]
  },
  "risk_settings": {
    "max_loss": 5000.00,
    "max_loss_pct": 50.0,
    "trailing_stop": {
      "enabled": true,
      "trigger_profit": 2000.00,
      "trail_amount": 1000.00
    },
    "time_stop": "15:15"
  },
  "schedule_config": {
    "activation_mode": "always",
    "active_days": ["MON", "TUE", "WED", "THU", "FRI"],
    "start_time": "09:15",
    "end_time": "15:30"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Strategy created successfully",
  "data": {
    "id": 1,
    "name": "Iron Condor Auto",
    "status": "draft",
    "...": "..."
  }
}
```

**Validation:**
- Maximum 50 strategies per user
- Strategy name must be unique per user
- At least 1 leg required (max 20)
- Leg IDs must be unique
- Entry conditions must be valid

---

### GET /strategies/{id}

Get complete strategy details including runtime state.

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Iron Condor Auto",
    "status": "active",
    "underlying": "NIFTY",
    "legs_config": [...],
    "entry_conditions": {...},
    "adjustment_rules": [...],
    "runtime_state": {
      "entered_at": "2025-12-21T09:25:00",
      "entry_price": {...},
      "current_positions": [
        {
          "leg_id": "leg_1",
          "tradingsymbol": "NIFTY25DEC24600CE",
          "transaction_type": "SELL",
          "quantity": 50,
          "average_price": 125.50,
          "last_price": 118.30,
          "unrealized_pnl": 360.00
        }
      ],
      "margin_used": 45000.00,
      "current_pnl": 1250.00,
      "max_pnl": 1800.00,
      "min_pnl": -200.00,
      "max_drawdown": 2000.00,
      "adjustments_made": [],
      "condition_states": {...},
      "last_updated": "2025-12-21T14:30:00"
    },
    "created_at": "2025-12-20T10:30:00",
    "updated_at": "2025-12-21T09:25:00",
    "activated_at": "2025-12-21T09:20:00"
  }
}
```

---

### PUT /strategies/{id}

Update strategy configuration (only draft or paused strategies).

**Request Body:** Same as POST, but all fields are optional
**Restrictions:**
- Can only update strategies in `draft` or `paused` status
- Cannot change underlying once strategy has been activated
- Increments version number

---

### DELETE /strategies/{id}

Delete a strategy.

**Restrictions:**
- Can only delete `draft`, `completed`, or `error` status strategies
- Cannot delete active/waiting/pending strategies
- Deletes all associated orders and logs

**Response:** 204 No Content

---

### POST /strategies/{id}/activate

Activate a draft strategy to start monitoring entry conditions.

**Request Body:**
```json
{
  "confirm": true,
  "paper_trading": false
}
```

**Pre-flight Checks:**
- Kite session is active
- Sufficient margin available (estimated + 20% buffer)
- Daily loss limit not breached
- Max active strategies not reached (default: 3)
- Schedule allows activation today
- All conditions are valid

**Status Change:** `draft` → `waiting`

**Response:**
```json
{
  "status": "success",
  "message": "Strategy activated successfully",
  "data": {
    "id": 1,
    "status": "waiting",
    "...": "..."
  }
}
```

**Paper Trading Mode:** Set `paper_trading: true` for simulation without real orders

---

### POST /strategies/{id}/pause

Pause an active strategy. Positions remain open.

**Effect:**
- Stops monitoring conditions
- Keeps positions open
- Can be resumed later

**Status Change:** `waiting`/`active`/`pending` → `paused`

**Response:**
```json
{
  "status": "success",
  "message": "Strategy paused",
  "data": {
    "id": 1,
    "status": "paused",
    "...": "..."
  }
}
```

---

### POST /strategies/{id}/resume

Resume a paused strategy.

**Pre-flight Checks:** Same as activation

**Status Change:** `paused` → `waiting` or `active` (based on position state)

---

### POST /strategies/{id}/exit

Force exit all positions and complete the strategy.

**Request Body:**
```json
{
  "confirm": true,
  "exit_type": "market",
  "reason": "Manual exit due to market volatility"
}
```

**Effect:**
- Cancels any pending orders
- Places exit orders for all positions
- Marks strategy as completed

**Status Change:** `active`/`paused`/`pending` → `completed`

**Response:**
```json
{
  "status": "success",
  "message": "Exit orders placed",
  "data": {
    "id": 1,
    "status": "completed",
    "...": "..."
  }
}
```

---

### POST /strategies/{id}/clone

Clone an existing strategy with new name.

**Request Body:**
```json
{
  "new_name": "Iron Condor Auto - Clone",
  "reset_schedule": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Strategy cloned successfully",
  "data": {
    "id": 2,
    "name": "Iron Condor Auto - Clone",
    "status": "draft",
    "cloned_from_id": 1,
    "...": "..."
  }
}
```

---

### GET /strategies/{id}/conditions

Get real-time condition evaluation states.

**Response:**
```json
{
  "status": "success",
  "data": {
    "strategy_id": 1,
    "strategy_status": "waiting",
    "entry_conditions": [
      {
        "condition_id": "cond_1",
        "condition_type": "entry",
        "variable": "TIME.CURRENT",
        "operator": "greater_equal",
        "target_value": "09:20",
        "current_value": "09:18",
        "is_satisfied": false,
        "progress_pct": 96.0,
        "distance_to_trigger": "2 minutes",
        "evaluated_at": "2025-12-21T09:18:00"
      },
      {
        "condition_id": "cond_2",
        "condition_type": "entry",
        "variable": "VIX.VALUE",
        "operator": "less_than",
        "target_value": 20.0,
        "current_value": 15.25,
        "is_satisfied": true,
        "progress_pct": 100.0,
        "distance_to_trigger": "Satisfied",
        "evaluated_at": "2025-12-21T09:18:00"
      }
    ],
    "adjustment_rules": {},
    "last_updated": "2025-12-21T09:18:00"
  }
}
```

**Use Case:** Real-time monitoring of how close conditions are to triggering

---

### POST /strategies/{id}/backtest

Run historical backtest for a strategy.

**Request Body:**
```json
{
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "initial_capital": 500000
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "strategy_id": 1,
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "total_trades": 22,
    "winning_trades": 15,
    "losing_trades": 7,
    "total_pnl": 18500.00,
    "max_drawdown": 4200.00,
    "win_rate": 68.18,
    "avg_profit": 1800.00,
    "avg_loss": -950.00,
    "sharpe_ratio": 1.85,
    "trades": [...]
  }
}
```

**Limitations:**
- Max backtest period: 365 days
- Requires historical market data

---

## Dashboard Endpoints

### GET /dashboard/summary

Dashboard overview with active strategies, P&L, and recent activity.

**Response:**
```json
{
  "status": "success",
  "data": {
    "active_strategies": 3,
    "waiting_strategies": 2,
    "total_pnl": 5200.00,
    "total_realized_pnl": 3800.00,
    "total_unrealized_pnl": 1400.00,
    "daily_pnl": 1250.00,
    "margin_used": 125000.00,
    "margin_available": 375000.00,
    "daily_loss_limit": 10000.00,
    "daily_loss_remaining": 8750.00,
    "recent_activity": [...]
  }
}
```

---

### GET /dashboard/activity

Activity feed with recent events.

**Query Parameters:**
- `limit` (default: 20) - Number of items

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "event_type": "entry_triggered",
      "severity": "info",
      "message": "Entry conditions satisfied for Iron Condor Auto",
      "strategy_id": 1,
      "strategy_name": "Iron Condor Auto",
      "timestamp": "2025-12-21T09:25:00"
    }
  ]
}
```

---

### GET /dashboard/risk

Risk metrics and alerts.

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_risk": 15000.00,
    "max_drawdown": 4200.00,
    "daily_loss": 1250.00,
    "daily_loss_limit": 10000.00,
    "active_alerts": [
      {
        "type": "risk_alert",
        "message": "Strategy approaching max loss limit",
        "strategy_id": 2
      }
    ]
  }
}
```

---

### GET /dashboard/performance

Performance statistics.

**Query Parameters:**
- `period` (default: "all") - all, today, week, month

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_trades": 45,
    "winning_trades": 32,
    "losing_trades": 13,
    "win_rate": 71.11,
    "avg_profit": 1850.00,
    "avg_loss": -920.00,
    "profit_factor": 2.15,
    "sharpe_ratio": 1.92,
    "total_pnl": 22400.00
  }
}
```

---

## Order Endpoints

### GET /orders/

List all AutoPilot orders with filters.

**Query Parameters:**
- `strategy_id` (optional) - Filter by strategy
- `purpose` (optional) - entry, adjustment, exit, hedge, etc.
- `status` (optional) - pending, placed, complete, rejected, etc.
- `page`, `page_size` - Pagination

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "strategy_id": 1,
      "batch_id": 1,
      "leg_id": "leg_1",
      "kite_order_id": "240122000123456",
      "purpose": "entry",
      "tradingsymbol": "NIFTY25DEC24600CE",
      "transaction_type": "SELL",
      "quantity": 50,
      "order_type": "MARKET",
      "status": "complete",
      "expected_price": 125.00,
      "executed_price": 124.50,
      "slippage": -0.50,
      "placed_at": "2025-12-21T09:25:00",
      "filled_at": "2025-12-21T09:25:15"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

---

### GET /orders/{id}

Get detailed order information.

---

### GET /orders/export

Export orders as CSV file.

**Query Parameters:** Same filters as list endpoint

**Response:** CSV file download

---

## Log Endpoints

### GET /logs/

List activity logs with filters.

**Query Parameters:**
- `strategy_id` (optional)
- `event_type` (optional) - entry_triggered, order_placed, etc.
- `severity` (optional) - info, warning, error
- `page`, `page_size`

---

### GET /logs/{id}

Get detailed log entry.

---

### GET /logs/export

Export logs as CSV file.

---

## Settings Endpoints

### GET /settings/

Get user's AutoPilot settings.

**Response:**
```json
{
  "status": "success",
  "data": {
    "daily_loss_limit": 10000.00,
    "max_active_strategies": 3,
    "kill_switch_enabled": false,
    "default_execution_mode": "auto",
    "delta_hedge_threshold": 0.30,
    "vega_hedge_threshold": 50.0,
    "notifications": {
      "email_enabled": true,
      "sms_enabled": false
    }
  }
}
```

---

### PUT /settings/

Update AutoPilot settings.

**Request Body:**
```json
{
  "daily_loss_limit": 15000.00,
  "max_active_strategies": 5,
  "default_execution_mode": "semi_auto"
}
```

---

## Template Endpoints

### GET /templates/

List pre-built strategy templates.

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Iron Condor Template",
      "category": "neutral",
      "risk_level": "medium",
      "description": "Neutral range-bound strategy",
      "strategy_config": {...}
    }
  ]
}
```

---

### GET /templates/{id}

Get template details.

---

### POST /templates/

Create new template from existing strategy.

---

### PUT /templates/{id}

Update template.

---

### DELETE /templates/{id}

Delete template.

---

## Emergency Endpoints

### POST /kill-switch/

Emergency stop all AutoPilot strategies.

**Request Body:**
```json
{
  "confirm": true,
  "reason": "Market volatility spike"
}
```

**Effect:**
- Pauses all active strategies
- Cancels all pending orders
- Optionally exits all positions

**Response:**
```json
{
  "status": "success",
  "message": "Kill switch activated",
  "data": {
    "strategies_paused": 3,
    "orders_cancelled": 5,
    "positions_exited": 12
  }
}
```

---

## WebSocket Connection

### WS /ws/stream

Real-time updates for AutoPilot events.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/autopilot/ws/stream?token=<jwt>')
```

**Message Types:**
- `STRATEGY_UPDATE` - Strategy status changed
- `PNL_UPDATE` - Real-time P&L update
- `CONDITION_EVALUATED` - Condition evaluation result
- `ORDER_PLACED` - Order placed
- `ORDER_FILLED` - Order filled
- `RISK_ALERT` - Risk limit breach warning
- `ADJUSTMENT_TRIGGERED` - Adjustment rule triggered
- `ERROR` - Error occurred

**Example Message:**
```json
{
  "type": "PNL_UPDATE",
  "data": {
    "strategy_id": 1,
    "current_pnl": 1250.00,
    "unrealized_pnl": 1250.00,
    "realized_pnl": 0.00,
    "timestamp": "2025-12-21T14:30:00"
  }
}
```

---

## Error Responses

All endpoints return standard error format:

```json
{
  "status": "error",
  "error": "ValidationError",
  "message": "Invalid strategy configuration",
  "details": [
    {
      "field": "legs_config",
      "message": "At least one leg required",
      "code": "MIN_LENGTH"
    }
  ],
  "timestamp": "2025-12-21T10:30:00",
  "request_id": "abc123"
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (e.g., max strategies reached)
- `422` - Unprocessable Entity (business logic error)
- `500` - Internal Server Error
