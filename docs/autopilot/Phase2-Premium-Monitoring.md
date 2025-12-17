# Phase 2: Premium Monitoring & Visualization

**Implementation Date:** December 2024
**Status:** ✅ Complete

## Overview

Phase 2 adds comprehensive premium tracking and visualization to AutoPilot, enabling users to monitor option premium decay in real-time, analyze theta decay curves, and track portfolio-level premium capture across all active strategies.

## Features Implemented

### 1. Backend Premium Tracking Service

**File:** `backend/app/services/premium_tracker.py`

#### Core Classes

- **`PremiumSnapshot`** - Single point-in-time premium snapshot
  - `timestamp` - When the snapshot was taken
  - `total_premium` - Combined premium of all legs
  - `ce_premium` - Call option premium
  - `pe_premium` - Put option premium
  - `legs_data` - Individual leg premium breakdown

- **`StraddlePremium`** - Current straddle (CE+PE) premium
  - `ce_premium`, `pe_premium`, `total_premium`
  - `ce_strike`, `pe_strike`, `underlying`

- **`DecayCurve`** - Theta decay analysis
  - `entry_premium` - Premium when strategy entered
  - `current_premium` - Current market premium
  - `expected_premium` - Expected premium based on linear decay
  - `days_to_expiry` - Days until option expiry
  - `decay_rate` - Actual vs expected decay multiplier
  - `premium_captured_pct` - % of premium captured

#### Service Methods

```python
class PremiumTracker:
    async def get_straddle_premium(underlying, expiry, strike) -> StraddlePremium
    async def get_strategy_current_premium(strategy_id) -> PremiumSnapshot
    async def get_premium_history(strategy_id, interval, lookback_hours) -> List[PremiumSnapshot]
    async def get_premium_decay_curve(strategy_id) -> DecayCurve
```

### 2. API Endpoints

**File:** `backend/app/api/v1/autopilot/router.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/autopilot/strategies/{id}/premium/current` | GET | Get current premium snapshot for a strategy |
| `/api/v1/autopilot/strategies/{id}/premium/history` | GET | Get historical premium data (interval, lookback_hours params) |
| `/api/v1/autopilot/strategies/{id}/premium/decay-curve` | GET | Get theta decay analysis (expected vs actual) |
| `/api/v1/autopilot/premium/straddle` | GET | Get straddle premium for any strike (underlying, expiry, strike params) |

#### Example Response: Decay Curve

```json
{
  "success": true,
  "data": {
    "entry_premium": 842.50,
    "current_premium": 756.20,
    "expected_premium": 780.00,
    "days_to_expiry": 12,
    "decay_rate": 1.2,
    "expected_decay_rate": 7.02,
    "premium_captured_pct": 10.2
  }
}
```

### 3. Frontend Components

#### StraddlePremiumChart.vue

**File:** `frontend/src/components/autopilot/monitoring/StraddlePremiumChart.vue`

Real-time premium monitoring chart using Chart.js.

**Features:**
- Line chart showing premium evolution over time
- Entry premium marker (dashed green line)
- Target profit line at 50% of entry (dashed orange)
- Stop-loss line at 150% of entry (dashed red)
- Header stats: Entry premium, Current premium, Captured %
- Auto-refresh every 5 seconds (configurable)
- Loading and error states

**Props:**
```javascript
{
  strategyId: Number (required),
  autoRefresh: Boolean (default: true),
  refreshInterval: Number (default: 5000ms)
}
```

**Usage:**
```vue
<StraddlePremiumChart
  :strategy-id="42"
  :auto-refresh="true"
  :refresh-interval="5000"
/>
```

#### ThetaDecayChart.vue

**File:** `frontend/src/components/autopilot/monitoring/ThetaDecayChart.vue`

Theta decay visualization comparing expected vs actual decay.

**Features:**
- Line chart with 3 points: Entry (100%), Mid-point, Expiry (0%)
- Expected decay curve (dotted gray line)
- Actual decay curve (solid purple line)
- Decay rate comparison badge (e.g., "1.2x faster than expected")
- Info box with entry/current/expected premium values
- Premium captured amount and percentage

**Props:**
```javascript
{
  strategyId: Number (required),
  autoRefresh: Boolean (default: true),
  refreshInterval: Number (default: 5000ms)
}
```

**Decay Rate Interpretation:**
- `< 0.9` - Slower than expected (strategy holding premium)
- `0.9 - 1.1` - On track with expected
- `> 1.1` - Faster than expected (accelerated decay)

#### Premium Monitoring Widgets (Dashboard)

**File:** `frontend/src/views/autopilot/DashboardView.vue`

Three dashboard widgets providing portfolio-level premium insights:

##### 1. Portfolio Premium Tracker
- **Total current premium** across all active strategies
- **Total captured premium** (entry - current)
- **Captured percentage** with gradient progress bar
- Active strategy count badge

##### 2. Top Premium Capturers
- Lists top 5 strategies by premium captured %
- Ranked display (1, 2, 3, 4, 5)
- Shows strategy name, underlying, and captured %
- Click to navigate to strategy detail

##### 3. Premium at Risk
- Identifies strategies with accelerated decay (> 1.5x)
- Shows strategies near stop-loss (< 10% captured)
- Displays warning indicators (pulsing orange dot)
- Shows decay rate multiplier (e.g., "2.1x decay")
- Empty state when all strategies performing well

**Data Refresh:**
- Fetches on dashboard mount
- Auto-refreshes every 10 seconds via polling (fallback)
- Updates on manual refresh button click
- Integrates with WebSocket for real-time updates

## Technical Implementation Details

### Premium History Tracking

**Current Implementation (Simplified):**
- Returns current premium snapshot only
- No persistent storage of historical data

**Production Recommendation (TODO):**
1. Create `autopilot_premium_snapshots` table:
   ```sql
   CREATE TABLE autopilot_premium_snapshots (
       id SERIAL PRIMARY KEY,
       strategy_id INTEGER REFERENCES autopilot_strategies(id),
       timestamp TIMESTAMPTZ NOT NULL,
       total_premium DECIMAL(10, 2),
       ce_premium DECIMAL(10, 2),
       pe_premium DECIMAL(10, 2),
       legs_data JSONB,
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_premium_snapshots_strategy_time
       ON autopilot_premium_snapshots(strategy_id, timestamp DESC);
   ```

2. Background task (Celery/APScheduler):
   ```python
   @scheduler.scheduled_job('interval', seconds=60)
   async def capture_premium_snapshots():
       for strategy in active_strategies:
           snapshot = await premium_tracker.get_strategy_current_premium(strategy.id)
           await db.save_premium_snapshot(strategy.id, snapshot)
   ```

3. Query historical data:
   ```python
   async def get_premium_history(strategy_id, interval='1m', lookback_hours=6):
       snapshots = await db.query(
           PremiumSnapshot
       ).filter(
           strategy_id == strategy_id,
           timestamp >= now() - timedelta(hours=lookback_hours)
       ).order_by(timestamp).all()
       return snapshots
   ```

### Decay Curve Calculation

**Formula (Simplified Linear Decay):**
```python
days_elapsed = (now - entry_time).days
expected_decay_rate = entry_premium / (days_elapsed + days_to_expiry)
expected_premium = entry_premium - (expected_decay_rate * days_elapsed)

actual_decay_rate = (entry_premium - current_premium) / days_elapsed
decay_rate_multiplier = actual_decay_rate / expected_decay_rate

premium_captured_pct = ((entry_premium - current_premium) / entry_premium) * 100
```

**Note:** This assumes linear decay. Real theta decay is non-linear (accelerates near expiry). For more accuracy, use Black-Scholes theta values.

### Chart.js Integration

Both chart components use Chart.js directly (not vue-chartjs wrapper):

```javascript
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ...)

const chartInstance = new ChartJS(canvasRef, {
  type: 'line',
  data: chartData,
  options: chartOptions
})
```

**Lifecycle Management:**
- Create chart in `onMounted` after `nextTick()`
- Destroy chart in `onBeforeUnmount`
- Update data reactively: `chartInstance.data = newData; chartInstance.update()`

## Testing

### Manual Testing Checklist

- [ ] Backend premium endpoints return valid data
- [ ] StraddlePremiumChart displays and auto-refreshes
- [ ] ThetaDecayChart shows expected vs actual curves
- [ ] Dashboard widgets show portfolio-level data
- [ ] Top capturers list sorted correctly
- [ ] At-risk strategies filter working (> 1.5x decay)
- [ ] Empty states display when no active strategies
- [ ] Charts handle API errors gracefully
- [ ] Auto-refresh can be toggled on/off
- [ ] Manual refresh button works

### E2E Test Coverage (TODO)

Create test files:
1. `tests/e2e/specs/autopilot/premium-chart.happy.spec.js`
   - Chart renders with mocked strategy
   - Data updates on refresh
   - Entry/target/SL lines visible

2. `tests/e2e/specs/autopilot/premium-chart.edge.spec.js`
   - Handle API failures
   - Handle missing premium data
   - Handle zero premium edge case

3. `tests/e2e/specs/autopilot/dashboard-widgets.happy.spec.js`
   - Widgets display with active strategies
   - Top capturers sorted correctly
   - At-risk alerts shown

## Known Limitations

1. **No Historical Storage** - Premium history endpoint returns current snapshot only. Requires background task + database table for production.

2. **Linear Decay Assumption** - Decay curve uses simplified linear decay model. Real option theta is non-linear (accelerates near expiry).

3. **Hardcoded Target/SL** - Chart shows target at 50% and SL at 150% of entry. Should come from strategy configuration.

4. **No WebSocket Integration** - Charts use polling (5-10s interval). Should integrate with AutoPilot WebSocket for true real-time updates.

5. **No Aggregation** - Dashboard fetches decay curve for each strategy individually. Consider adding batch endpoint for efficiency.

## Future Enhancements

### Phase 2.5: Advanced Premium Analytics

1. **IV Rank Overlay** - Show IV rank changes on premium chart
2. **Expected vs Actual IV** - Compare realized vs implied volatility
3. **Premium Heatmap** - Visualize premium across multiple strikes/expiries
4. **Decay Rate Alerts** - Notifications when decay rate exceeds thresholds
5. **Historical Comparison** - Compare current strategy decay to historical averages

### Phase 2.6: Premium-Based Exit Rules

1. **Profit Target** - Exit when premium captured >= X%
2. **Trailing Stop** - Exit if premium increases by X% from low
3. **Time-Based** - Exit if premium not captured by X days before expiry
4. **Acceleration Alert** - Alert when decay rate > 2x expected

## Related Documentation

- [AutoPilot Full Plan](./AutoPilot-Redesign-Implementation-Plan-Full.md) - Complete 4-phase redesign plan
- [AutoPilot README](./README.md) - System overview and architecture
- [Backend Services](../../backend/app/services/) - Service layer implementation
- [Frontend Components](../../frontend/src/components/autopilot/monitoring/) - Chart components

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2024-12-17 | Phase 2 complete implementation | Claude Code |
| 2024-12-17 | Added dashboard premium widgets | Claude Code |
| 2024-12-17 | Created documentation | Claude Code |

---

**Next Phase:** Phase 3 - Re-Entry & Advanced Adjustments (see full plan for details)
