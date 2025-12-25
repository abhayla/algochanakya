# AI Configuration & Settings

**Feature Status:** ✅ Implemented (Week 2 - December 2025)

Autonomous AI trading configuration system that enables users to configure AI-powered strategy deployment, position sizing, and risk management parameters.

## Overview

The AI Configuration feature provides a comprehensive settings interface for controlling autonomous trading behavior. Users can configure deployment schedules, position sizing strategies with confidence-based tiers, hard limits for risk management, and track paper trading graduation progress.

This feature is part of the **AutoPilot AI Autonomous Trading System** and provides the foundational configuration layer that controls how AI strategies are deployed and executed.

## Key Features

### 1. Autonomy Settings
- **AI Trading Toggle:** Enable/disable autonomous trading
- **Trading Mode:** Paper trading vs. Live trading (requires graduation)
- **Paper Trading Graduation:** Track progress toward live trading eligibility (25 trades, 55% win rate, 15 days)

### 2. Deployment Schedule
- **Auto-Deploy Toggle:** Enable/disable automatic strategy deployment
- **Deploy Time:** Set time of day for strategy deployment (HH:MM format)
- **Deploy Days:** Select which weekdays to deploy (Mon-Fri)
- **Event Day Skipping:** Automatically skip deployment on major market events (Budget, RBI policy, etc.)
- **Weekly Expiry Skipping:** Option to skip Thursday (weekly expiry day)

### 3. Position Sizing
- **Sizing Modes:**
  - Fixed: Same lot size for all trades
  - Tiered: Confidence-based lot sizing with multipliers
  - Kelly Criterion: (Placeholder for Week 9)
- **Base Lots:** Baseline lot size for position sizing calculations
- **Confidence Tiers:** Configurable tiers with min/max confidence ranges and multipliers
  - Default: SKIP (0-59, 0x), LOW (60-74, 1.0x), MEDIUM (75-84, 1.5x), HIGH (85-100, 2.0x)

### 4. Trading Limits
- **Max Lots per Strategy:** Limit lot size for individual strategies
- **Max Lots per Day:** Daily aggregate lot limit
- **Max Strategies per Day:** Maximum number of strategies to deploy per day
- **Min Confidence to Trade:** Minimum confidence threshold (0-100%)
- **Max VIX to Trade:** Maximum VIX level for deployment
- **Weekly Loss Limit:** Maximum weekly loss limit (₹)

### 5. AI Explanations (Future)
- **Claude API Key:** Store encrypted Claude API key for AI explanations
- **Enable Explanations:** Toggle AI-powered strategy explanations

## Architecture

### Backend

**Database:**
- **Table:** `ai_user_config` (migration 010_ai_week2_user_config.py)
- **Relationship:** One-to-one with users table
- **Storage:** JSONB for confidence tiers and allowed strategies

**API Endpoints:**
- `GET /api/v1/ai/config` - Get user configuration (creates defaults if missing)
- `PUT /api/v1/ai/config` - Update configuration
- `GET /api/v1/ai/config/defaults` - Get default configuration template
- `GET /api/v1/ai/config/strategies` - Get allowed strategy templates
- `PUT /api/v1/ai/config/strategies` - Update allowed strategies
- `GET /api/v1/ai/config/sizing` - Get position sizing config
- `PUT /api/v1/ai/config/sizing` - Update position sizing
- `POST /api/v1/ai/config/validate-claude` - Validate Claude API key
- `GET /api/v1/ai/config/paper-trading/status` - Get graduation status

**Services:**
- **AIConfigService** (`backend/app/services/ai/config_service.py`)
  - Configuration CRUD operations
  - Lot size calculation based on confidence
  - Deployment day validation
  - Limit checking
  - Claude API key validation
  - Paper trading graduation checking

**Models:**
- **AIUserConfig** (`backend/app/models/ai.py`) - SQLAlchemy model with 20+ configuration fields

**Schemas:**
- **Pydantic Schemas** (`backend/app/schemas/ai.py`)
  - AIUserConfigResponse, AIUserConfigUpdate
  - PositionSizingConfig, DeploymentScheduleConfig, AILimitsConfig
  - ConfidenceTier, PaperTradingStatus
  - Comprehensive validation with field validators

### Frontend

**Views:**
- **AISettingsView.vue** - Main configuration UI with 5 panels
  - Autonomy Settings Panel
  - Deployment Schedule Panel
  - Position Sizing Panel
  - Trading Limits Panel
  - Action buttons (Save, Reset to Defaults)

**Stores:**
- **aiConfig Store** (`frontend/src/stores/aiConfig.js`)
  - State: config, loading, saving, error
  - Getters: isAIEnabled, autonomyMode, canGraduateToLive, lotsForConfidence
  - Actions: fetchConfig, saveConfig, updateStrategies, validateClaudeKey, resetToDefaults

**Navigation:**
- Route: `/ai/settings` with auth requirement
- Header link with brain icon

## Usage

### Configuring Position Sizing

1. **Fixed Sizing:**
   - Set `sizing_mode` to "fixed"
   - Configure `base_lots` (e.g., 1)
   - All trades use same lot size

2. **Tiered Sizing:**
   - Set `sizing_mode` to "tiered"
   - Configure `base_lots` (e.g., 1)
   - Define confidence tiers with multipliers
   - Example: 75% confidence = 1.5x lots, 90% confidence = 2.0x lots

### Setting Deployment Schedule

```
Enable Auto-Deploy: ✓
Deploy Time: 09:20
Deploy Days: Mon, Tue, Wed, Thu, Fri
Skip Event Days: ✓
Skip Weekly Expiry: ✗
```

This configuration deploys strategies at 9:20 AM on weekdays, skipping major event days but including Thursday (weekly expiry).

### Paper Trading Graduation

To graduate from paper to live trading, users must meet:
- **25 completed trades** in paper mode
- **55% win rate** or higher
- **15 days** of paper trading experience
- **Manual approval** from admin (for safety)

Progress is tracked in the Paper Trading Status section.

## Configuration Flow

```
User opens AI Settings
  ↓
Frontend fetches config via GET /api/v1/ai/config
  ↓
Backend checks if config exists
  ↓
If missing: Create with defaults
If exists: Return existing config
  ↓
User modifies settings (auto-save with 2s debounce)
  ↓
Frontend sends PUT /api/v1/ai/config
  ↓
Backend validates updates (Pydantic schemas)
  ↓
Backend saves to database
  ↓
Returns updated config to frontend
```

## Validation Rules

**Confidence Tiers:**
- Must cover full 0-100 range with no gaps
- No overlaps between tiers
- Multiplier must be >= 0
- At least one tier must have multiplier > 0 (else no trades possible)

**Deployment Days:**
- Must be one of: MON, TUE, WED, THU, FRI
- At least one day must be selected for auto-deploy

**Limits:**
- All lot limits must be positive integers
- Confidence range: 0-100
- VIX must be positive decimal
- Weekly loss limit must be positive

## Integration with AutoPilot

The AI Configuration feature directly controls AutoPilot behavior:
- **Strategy Monitor** checks `ai_enabled` before deploying strategies
- **Deployment Scheduler** uses `deploy_time`, `deploy_days`, and skip rules
- **Position Sizing** uses `calculate_lots_for_confidence()` to determine lot sizes
- **Risk Management** enforces limits via `is_within_limits()` checks

## Default Configuration

New users receive these default settings:
```python
ai_enabled: False
autonomy_mode: "paper"
auto_deploy_enabled: False
deploy_time: "09:20"
deploy_days: ["MON", "TUE", "WED", "THU", "FRI"]
skip_event_days: True
skip_weekly_expiry: False
sizing_mode: "tiered"
base_lots: 1
confidence_tiers: [
  {name: "SKIP", min: 0, max: 59, multiplier: 0},
  {name: "LOW", min: 60, max: 74, multiplier: 1.0},
  {name: "MEDIUM", min: 75, max: 84, multiplier: 1.5},
  {name: "HIGH", min: 85, max: 100, multiplier: 2.0}
]
max_lots_per_strategy: 2
max_lots_per_day: 6
max_strategies_per_day: 5
min_confidence_to_trade: 60.0
max_vix_to_trade: 25.0
weekly_loss_limit: 50000.00
```

## Testing

**E2E Tests:** `tests/e2e/specs/ai/` (to be created)

Test coverage includes:
- Configuration loading and creation
- Form validation
- Auto-save functionality
- Reset to defaults
- Paper trading status display
- Live mode lock until graduation

## Future Enhancements (Week 3+)

- **Strategy Universe Management:** UI for selecting allowed strategy templates
- **Advanced Tier Editor:** Visual tier builder with drag-and-drop
- **Kelly Criterion:** Implement Kelly-based position sizing (Week 9)
- **AI Explanations:** Claude-powered strategy explanations and recommendations
- **Backtesting Integration:** Test configurations against historical data
- **Risk Profiles:** Pre-built risk profiles (Conservative, Moderate, Aggressive)

## Related Features

- **AutoPilot:** Uses AI Config for strategy execution
- **Strategy Builder:** Can inherit position sizing logic

## Files

**Backend:**
- `backend/alembic/versions/010_ai_week2_user_config.py`
- `backend/app/models/ai.py`
- `backend/app/schemas/ai.py`
- `backend/app/services/ai/config_service.py`
- `backend/app/api/v1/ai/config.py`
- `backend/app/api/v1/ai/router.py`

**Frontend:**
- `frontend/src/views/ai/AISettingsView.vue`
- `frontend/src/stores/aiConfig.js`
- `frontend/src/router/index.js` (route registration)
- `frontend/src/components/layout/KiteHeader.vue` (navigation link)

## Documentation

- [REQUIREMENTS.md](./REQUIREMENTS.md) - Feature requirements checklist
- [CHANGELOG.md](./CHANGELOG.md) - Version history
- [AutoPilot Docs](../autopilot/) - AutoPilot system documentation
