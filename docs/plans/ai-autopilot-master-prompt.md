# AutoPilot AI Autonomous Implementation

You are implementing the complete 12-week AutoPilot AI plan for AlgoChanakya autonomously.

---

## ⚡ FIRST: Read State and Resume

1. **Read current position:** `docs/plans/ai-implementation-state.json`
   - If file doesn't exist, this is a fresh start - initialize state and begin from Week 1
   - If file exists, resume from `currentWeek` and `currentTask`

2. **Read the full plan:** `docs/plans/autopilot-ai-autonomous-implementation-plan.md`
   - Understand the requirements for current week
   - Review deliverables checklist for current task

3. **Check what's already done:**
   - Week 1-2: COMPLETE (Market Intelligence + AI Config)
   - Week 3: ~20% complete (AutoPilot metadata added)
   - Week 4-12: NOT STARTED

---

## 🔐 Authentication

Before starting any work, validate authentication:

1. **Check auth token validity:**
   ```javascript
   // Read token from file
   const authState = JSON.parse(fs.readFileSync('tests/config/.auth-state.json'))
   const token = authState.origins[0].localStorage.find(item => item.name === 'access_token').value

   // Validate via API
   GET /api/auth/me (Authorization: Bearer <token>)
   GET /api/auth/broker/validate (Authorization: Bearer <token>)
   ```

2. **If token is expired or missing:**
   - STOP and ASK USER: "Auth token expired. Please provide TOTP code for Zerodha login."
   - Wait for user to provide TOTP
   - Perform OAuth login flow
   - Save new token to `tests/config/.auth-token` and `.auth-state.json`

3. **For Claude Chrome testing:**
   - Start Chrome with: `/chrome` or check connection
   - Navigate to: `http://localhost:5173`
   - Inject token: `localStorage.setItem('access_token', '<token>')`
   - Reload page and verify authentication

---

## 🔄 Implementation Workflow

### For Each Task:

1. **READ** the task requirements from the plan
2. **IMPLEMENT** the code following existing patterns
3. **TEST** with E2E tests + Claude Chrome verification
4. **UPDATE** progress state (JSON + MD)
5. **COMMIT** if feature milestone complete (optional)

### Per-Feature Verification Checkpoints:

After implementing each feature/component, verify using **Claude Chrome**:

1. **Navigate** to the relevant screen URL
2. **Visual Check** - UI renders correctly, no layout issues
3. **Console Check** - No errors in browser console
4. **Interaction Check** - Click buttons, fill forms, test key flows
5. **Screenshot** - Capture if needed for documentation
6. **Data Check** - API returns valid responses

**Feature URLs:**
- AI Settings: `http://localhost:5173/ai/settings`
- Regime API: `http://localhost:8000/api/v1/ai/regime/current`
- Indicators API: `http://localhost:8000/api/v1/ai/regime/indicators`
- Paper Trading: `http://localhost:5173/ai/paper-trading` (Week 4)
- Analytics: `http://localhost:5173/ai/analytics` (Week 8)

---

## ❌ Failure Handling

### Critical Failures (STOP and ASK USER):
- **Database migration errors** - Don't proceed with broken schema
- **Core service failures** - `order_executor.py`, `position_sync.py`, `strategy_monitor.py`
- **API endpoint errors** - Routes not working, returning 500
- **Authentication failures** - Cannot authenticate or validate tokens
- **Test failures after 5 attempts** - Cannot fix automatically

### Non-Critical Failures (LOG and CONTINUE):
- Documentation formatting issues
- Comment additions
- Minor UI styling tweaks
- Screenshot capture failures

---

## 🎨 UI Style Requirements

**IMPORTANT:** Follow existing Kite-style patterns from `frontend/src/assets/styles/kite-theme.css`

### Colors (USE CSS VARIABLES):
```css
/* Primary Colors */
--kite-primary: #387ed1        /* Kite Blue */
--kite-green: #00b386          /* Profit Green */
--kite-red: #e53935            /* Loss Red */
--kite-blue: #387ed1           /* Info Blue */
--kite-orange: #ff9800         /* Warning Orange */

/* Text Colors */
--kite-text-primary: #394046   /* Main text */
--kite-text-secondary: #6c757d /* Secondary text */
--kite-text-muted: #9aa3ad     /* Muted text */

/* Backgrounds */
--kite-body-bg: #ffffff        /* Pure white */
--kite-card-bg: #ffffff        /* Card background */

/* Borders & Shadows */
--kite-border: #e8e8e8         /* Border color */
--kite-shadow-sm: 0 1px 3px rgba(0,0,0,0.04)
--kite-shadow: 0 2px 6px rgba(0,0,0,0.06)
```

### Component Patterns:
```html
<!-- Card -->
<div class="bg-white rounded-lg shadow p-6">
  <h2 class="text-lg font-semibold mb-4">Title</h2>
  <p class="text-sm text-gray-600">Content</p>
</div>

<!-- Button (Primary) -->
<button class="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700">
  Action
</button>

<!-- Input -->
<input class="border rounded px-3 py-2 focus:border-blue-500 focus:outline-none w-full">

<!-- Badge/Status -->
<span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
  Active
</span>
```

### Required Conventions:
- **data-testid** on ALL interactive elements (buttons, inputs, links)
- **Scoped styles** - Use `<style scoped>` in Vue components
- **Follow existing patterns** - Check `frontend/src/components/autopilot/` for reference
- **Small border radius** - 4px for cards/inputs, pill for badges
- **Subtle shadows** - Use `--kite-shadow-sm`
- **System font stack** - No custom fonts

---

## 🗄️ Database Migrations

**IMPORTANT:** Migrations must be handled carefully to avoid data loss.

### Before Applying Migration:

1. **Backup database:**
   ```bash
   pg_dump -h 103.118.16.189 -U <user> -d algochanakya > backup_week<N>_$(date +%Y%m%d).sql
   ```

2. **Generate migration:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "week <N>: <description>"
   ```

3. **Review migration file** - Check generated SQL for correctness

4. **Apply migration:**
   ```bash
   alembic upgrade head
   ```

5. **Verify migration** - Run tests to ensure schema is correct

6. **If tests fail:**
   ```bash
   alembic downgrade -1  # Rollback
   # Fix issue, then ask user
   ```

### Migration Files Created So Far:
- ✅ `009_ai_week1_market_intelligence.py` - ai_market_snapshots table
- ✅ `010_ai_week2_user_config.py` - ai_user_config table
- ✅ `011_ai_week3_autopilot_integration.py` - AI metadata columns

---

## 📊 Progress Tracking

### Update State After Each Task:

```javascript
// docs/plans/ai-implementation-state.json
{
  "version": "1.0",
  "planFile": "docs/plans/autopilot-ai-autonomous-implementation-plan.md",
  "currentPhase": "MVP",              // MVP, Enhancement, Optimization
  "currentWeek": 3,
  "currentTask": "strategy_recommender.py",
  "status": "in_progress",            // not_started, in_progress, complete
  "lastUpdated": "2024-12-25T10:30:00Z",
  "startedAt": "2024-12-25T09:00:00Z",
  "completedWeeks": [1, 2],
  "completedTasks": [
    "backend/app/services/ai/historical_data.py",
    "backend/app/services/ai/indicators.py",
    // ... all completed tasks
  ],
  "failedTasks": [],
  "testResults": {
    "passed": 127,
    "failed": 0,
    "skipped": 3
  },
  "authStatus": {
    "lastValidated": "2024-12-25T09:00:00Z",
    "isValid": true
  },
  "notes": [
    "Week 1-2 already complete",
    "Week 3: 20% complete, need strategy_recommender.py"
  ]
}
```

### Update Progress Markdown:

```markdown
// docs/plans/ai-implementation-progress.md

## Current Status
- **Phase:** MVP (Weeks 1-4)
- **Week:** 3
- **Status:** In Progress
- **Last Updated:** 2024-12-25 10:30 IST

## Session Log
| Session | Date | Week | Tasks Completed | Notes |
|---------|------|------|-----------------|-------|
| 1 | 2024-12-25 | 3 | strategy_recommender.py | Created strategy scoring logic |
```

---

## 🔚 Session End Protocol

When context limit is approaching (>180K tokens) or natural checkpoint:

1. **Update State Files:**
   - `docs/plans/ai-implementation-state.json` - Update current position
   - `docs/plans/ai-implementation-progress.md` - Add session log entry

2. **Output Message:**
   ```
   Session complete. Progress saved.

   Completed: <list of tasks>
   Next up: <next task>

   To continue, paste the same prompt from:
   docs/plans/ai-autopilot-master-prompt.md
   ```

3. **Optional:** Commit progress if at feature milestone

---

## 📋 Week-by-Week Implementation Checklist

### ✅ Week 1: Market Intelligence Engine (COMPLETE)
- [x] backend/app/services/ai/__init__.py
- [x] backend/app/services/ai/historical_data.py
- [x] backend/app/services/ai/indicators.py
- [x] backend/app/services/ai/market_regime.py
- [x] Migration: ai_market_snapshots table
- [x] API: GET /api/v1/ai/regime/current
- [x] API: GET /api/v1/ai/regime/indicators

### ✅ Week 2: AI Configuration & Settings (COMPLETE)
- [x] Migration: ai_user_config table
- [x] backend/app/api/v1/ai/router.py
- [x] backend/app/api/v1/ai/config.py
- [x] backend/app/api/v1/ai/schemas.py
- [x] backend/app/models/ai.py
- [x] frontend/src/views/ai/AISettingsView.vue
- [x] frontend/src/stores/aiConfig.js

### ⚠️ Week 3: Auto-Deployment & Position Sync (20% COMPLETE)
- [x] Migration: 011_ai_week3_autopilot_integration.py
- [ ] backend/app/services/ai/strategy_recommender.py
- [ ] backend/app/services/ai/strike_selector.py
- [ ] backend/app/services/ai/claude_advisor.py
- [ ] backend/app/services/ai/daily_scheduler.py
- [ ] backend/app/services/ai/deployment_executor.py
- [ ] backend/app/services/ai/position_sync.py
- [ ] Migration: ai_scheduled_deployments table
- [ ] Migration: ai_position_sync_events table
- [ ] API: GET /api/v1/ai/recommendations
- [ ] API: POST /api/v1/ai/deploy
- [ ] E2E tests for auto-deployment

### ❌ Week 4: Integration & Paper Trading
- [ ] backend/app/services/ai/ai_monitor.py
- [ ] Migration: ai_decisions_log table
- [ ] Integrate AI hooks into strategy_monitor.py
- [ ] frontend/src/views/ai/PaperTradingView.vue
- [ ] frontend/src/components/ai/MarketRegimeIndicator.vue
- [ ] frontend/src/components/ai/AIDecisionCard.vue
- [ ] frontend/src/components/ai/GraduationProgress.vue
- [ ] E2E test: End-to-end paper trading flow
- [ ] Claude API integration test

### ❌ Week 5: ML Strategy Scorer
- [ ] backend/app/services/ai/ml/feature_extractor.py
- [ ] backend/app/services/ai/ml/strategy_scorer.py
- [ ] backend/app/services/ai/ml/training_pipeline.py
- [ ] backend/app/services/ai/ml/model_registry.py
- [ ] Migration: ai_model_registry table
- [ ] Initial model training script
- [ ] Unit tests for ML features

### ❌ Week 6: Intelligent Adjustment Engine
- [ ] backend/app/services/ai/ai_adjustment_advisor.py
- [ ] Integrate with existing adjustment_engine.py
- [ ] What-if simulation for adjustments
- [ ] Auto-execute adjustments in full-auto mode
- [ ] E2E tests for AI adjustments

### ❌ Week 7: Self-Learning Pipeline
- [ ] backend/app/services/ai/learning_pipeline.py
- [ ] backend/app/services/ai/feedback_scorer.py
- [ ] Migration: ai_learning_reports table
- [ ] Daily learning job in scheduler
- [ ] Claude-generated insights
- [ ] Model retraining trigger

### ❌ Week 8: Performance Analytics Dashboard
- [ ] backend/app/api/v1/ai/analytics.py
- [ ] frontend/src/views/ai/AnalyticsView.vue
- [ ] Performance charts (Chart.js)
- [ ] Regime performance breakdown
- [ ] Strategy performance breakdown
- [ ] Export reports (PDF/CSV)

### ❌ Week 9: Kelly Criterion Position Sizing
- [ ] backend/app/services/ai/kelly_calculator.py
- [ ] Integrate Kelly sizing with position sizing service
- [ ] UI option to enable Kelly sizing
- [ ] Unit tests for Kelly calculation

### ❌ Week 10: Advanced Backtesting
- [ ] backend/app/services/ai/backtester.py
- [ ] Backtest API endpoints
- [ ] Backtest UI view
- [ ] Historical data for past 6 months

### ❌ Week 11: Multi-Strategy Orchestration
- [ ] Portfolio Greeks aggregation
- [ ] Cross-strategy correlation analysis
- [ ] Portfolio rebalancing suggestions
- [ ] Multi-strategy dashboard view

### ❌ Week 12: Production Hardening
- [ ] Error recovery mechanisms
- [ ] Alerting system (email/push)
- [ ] Performance metrics (latency, success rate)
- [ ] Security audit
- [ ] Documentation updates
- [ ] Production deployment checklist

---

## 🎯 Success Criteria

The implementation is complete when:

1. ✅ All 12 weeks implemented
2. ✅ All E2E tests pass (`npm test`)
3. ✅ All API endpoints return valid responses
4. ✅ Claude Chrome verification passes for all screens
5. ✅ Paper trading mode works end-to-end (9:20 AM deploy → monitor → exit)
6. ✅ Live trading mode ready (post paper-trading graduation)
7. ✅ ML models trained and scoring strategies
8. ✅ Self-learning pipeline running daily
9. ✅ Documentation updated

---

## 📝 Important Notes

- **Self-Resuming:** This same prompt works for every session
- **State-Driven:** Always read `ai-implementation-state.json` first
- **Critical Failures:** Stop and ask user to prevent broken foundation
- **UI Consistency:** Match Kite style with CSS variables
- **Testing:** E2E + Claude Chrome + selective unit tests
- **ANTHROPIC_API_KEY:** Should be in backend/.env
- **Database:** Remote PostgreSQL (103.118.16.189) - backup before migrations

---

## 🚀 Begin Implementation

1. Read state file: `docs/plans/ai-implementation-state.json`
2. Validate auth token
3. Continue from current position
4. Update progress after each task
5. Use Claude Chrome for visual verification
6. Stop and ask on critical failures

**Current Position:** Read from state file to determine where to resume.
