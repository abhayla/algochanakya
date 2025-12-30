# AI Autopilot Paper Trading Testing - Implementation Plan

## Executive Summary

Comprehensive testing of AI Autopilot paper trading feature with manual deploy trigger, paper trade exit, and ~15 test cases covering all 3 position sizing modes (Fixed, Tiered, Kelly).

## User Requirements (Confirmed via Q&A)

| Aspect | Choice |
|--------|--------|
| **Feature** | AI Autopilot only (`/ai/*` routes) |
| **Test Scope** | AI auto-deployment with paper trading |
| **Trigger Method** | Create test endpoint `POST /api/v1/ai/deploy/trigger` |
| **Coverage** | Representative subset (~10-15 cases): NIFTY + current regime + 3 position sizing modes |
| **Exit Handling** | Create endpoint `POST /api/v1/ai/paper-trade/exit` |
| **Verification** | Screenshots verified against UI state + API data (no errors) |
| **Testing Mode** | Headed browser with Claude Chrome |
| **Fix Loop** | Fix any issues found, retest until pass |

---

## Part 1: Backend Implementation

### 1.1 Create New Router: `deploy.py`

**Location:** `backend/app/api/v1/ai/deploy.py`

#### Endpoint 1: `POST /api/v1/ai/deploy/trigger`
```python
class DeployTriggerRequest(BaseModel):
    underlying: str = Field(..., description="NIFTY, BANKNIFTY, FINNIFTY")
    force: bool = Field(False, description="Bypass VIX/time checks for testing")

class DeployTriggerResponse(BaseModel):
    success: bool
    deployment_id: Optional[str]
    strategy_name: Optional[str]
    legs: List[dict]
    order_ids: List[str]  # PAPER_0, PAPER_1, etc.
    confidence: float
    regime: str
    position_size_lots: int
    sizing_mode: str
    error: Optional[str]
```

**Implementation:**
1. Get user config via `AIConfigService.get_or_create_config()`
2. Validate AI is enabled
3. Get current regime via `MarketRegimeClassifier`
4. Get strategy recommendation via `StrategyRecommender`
5. Calculate lots based on `sizing_mode`
6. Deploy via `DeploymentExecutor.deploy_strategy()` with `paper_mode=True`
7. Store paper trade in `AIPaperTrade` model
8. Return deployment result

#### Endpoint 2: `POST /api/v1/ai/paper-trade/exit`
```python
class PaperExitRequest(BaseModel):
    paper_trade_id: str
    exit_reason: str = "manual"

class PaperExitResponse(BaseModel):
    success: bool
    paper_trade_id: str
    entry_pnl: float
    exit_pnl: float
    realized_pnl: float
    hold_time_minutes: int
    exit_reason: str
    error: Optional[str]
```

#### Endpoint 3: `GET /api/v1/ai/paper-trade/list`
Returns active and closed paper trades with summary.

### 1.2 Create Model: `AIPaperTrade`

**Location:** Add to `backend/app/models/ai.py`

```python
class AIPaperTrade(Base):
    __tablename__ = "ai_paper_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    underlying = Column(String(20), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    entry_regime = Column(String(30), nullable=False)
    entry_confidence = Column(Numeric(5,2), nullable=False)
    sizing_mode = Column(String(20), nullable=False)
    lots = Column(Integer, nullable=False)
    legs = Column(JSONB, nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_reason = Column(String(50), nullable=True)
    entry_total_premium = Column(Numeric(12,2), nullable=False)
    exit_total_premium = Column(Numeric(12,2), nullable=True)
    realized_pnl = Column(Numeric(12,2), nullable=True)
    status = Column(String(20), default='open')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 1.3 Update Router Registration

**File:** `backend/app/api/v1/ai/router.py`

```python
from app.api.v1.ai import deploy
router.include_router(deploy.router, prefix="/deploy", tags=["ai-deploy"])
```

---

## Part 2: Frontend Implementation

### 2.1 Update PaperTradingView.vue

**File:** `frontend/src/views/ai/PaperTradingView.vue`

**Add:**
1. Deploy trigger button with `data-testid="btn-trigger-deploy"`
2. Paper trades table with `data-testid="paper-trades-table"`
3. Exit button per row with `data-testid="btn-exit-trade-{id}"`
4. API methods for `triggerDeploy()` and `exitTrade()`

---

## Part 3: Test Cases (15 total)

### Suite 1: AI Settings Configuration (4 tests)

| # | Test Case | Expected Outcome | Screenshot |
|---|-----------|------------------|------------|
| 1 | Enable AI + paper mode | AI enabled, mode = paper | `ai-settings-enabled.png` |
| 2 | Set sizing to Fixed | sizing_mode = fixed | `ai-settings-fixed.png` |
| 3 | Set sizing to Tiered | sizing_mode = tiered | `ai-settings-tiered.png` |
| 4 | Set sizing to Kelly | sizing_mode = kelly | `ai-settings-kelly.png` |

### Suite 2: Paper Trading - Fixed Sizing (3 tests)

| # | Test Case | Expected Outcome | Screenshot |
|---|-----------|------------------|------------|
| 5 | Trigger deploy (Fixed) | Paper trade created, lots = base_lots | `deploy-fixed.png` |
| 6 | Verify trade displayed | Trade row shows correct data | `trade-row-fixed.png` |
| 7 | Exit position | P&L calculated, trade closed | `exit-fixed.png` |

### Suite 3: Paper Trading - Tiered Sizing (3 tests)

| # | Test Case | Expected Outcome | Screenshot |
|---|-----------|------------------|------------|
| 8 | Configure tiered | Config saved | `config-tiered.png` |
| 9 | Deploy (Tiered) | lots = base_lots * multiplier | `deploy-tiered.png` |
| 10 | Exit position | P&L calculated | `exit-tiered.png` |

### Suite 4: Paper Trading - Kelly Sizing (3 tests)

| # | Test Case | Expected Outcome | Screenshot |
|---|-----------|------------------|------------|
| 11 | Configure kelly | Config saved | `config-kelly.png` |
| 12 | Deploy (Kelly) | Lots via Kelly formula | `deploy-kelly.png` |
| 13 | Exit position | P&L calculated | `exit-kelly.png` |

### Suite 5: Error Cases & UI (2 tests)

| # | Test Case | Expected Outcome | Screenshot |
|---|-----------|------------------|------------|
| 14 | Deploy with AI disabled | Error: "AI not enabled" | `error-ai-disabled.png` |
| 15 | UI elements check | All components visible, no errors | `ui-complete.png` |

---

## Part 4: Screenshot Verification Criteria

### AI Settings Screenshots:
- Toggle state matches expected
- Sizing mode dropdown shows correct value
- No error banners visible

### Paper Trading Screenshots:
- Regime indicator visible in header
- Paper trades table rendered
- Trade rows show: strategy, entry time, regime, lots, sizing mode, P&L

### Deploy/Exit Screenshots:
- Success toast after completion
- Table updated with new/modified trade
- P&L values formatted correctly

### Error Screenshots:
- Error message visible
- Deploy button disabled when appropriate

---

## Part 5: Critical Files

| Component | File Path |
|-----------|-----------|
| Deploy Router (NEW) | `backend/app/api/v1/ai/deploy.py` |
| AI Model (ADD) | `backend/app/models/ai.py` |
| Paper Trading View | `frontend/src/views/ai/PaperTradingView.vue` |
| AI Settings View | `frontend/src/views/ai/AISettingsView.vue` |
| Deployment Executor | `backend/app/services/ai/deployment_executor.py` |
| Daily Scheduler | `backend/app/services/ai/daily_scheduler.py` |
| AI Router | `backend/app/api/v1/ai/router.py` |

---

## Part 6: Implementation Sequence

### Phase 1: Backend
1. Create `AIPaperTrade` model
2. Run migration
3. Create `deploy.py` router with 3 endpoints
4. Register router
5. Test endpoints via curl

### Phase 2: Frontend
1. Update `PaperTradingView.vue` with buttons and table
2. Add API methods
3. Add data-testid attributes
4. Test manually

### Phase 3: Test Creation
1. Create page objects (`AIPaperTradingPage.js`, `AISettingsPage.js`)
2. Write test spec file
3. Run tests headed

### Phase 4: Execution & Fixes
1. Run all 15 tests
2. Capture screenshots
3. Fix issues found
4. Re-run until all pass

---

## Test Execution Commands

```bash
# Run headed
npx playwright test tests/e2e/specs/ai/ai-paper-trading.spec.js --headed

# Debug mode
npx playwright test tests/e2e/specs/ai/ai-paper-trading.spec.js --debug

# Single test
npx playwright test tests/e2e/specs/ai/ai-paper-trading.spec.js -g "Enable AI"
```
