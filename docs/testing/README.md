# Comprehensive Test Architecture for AlgoChanakya

## Overview
A complete, auto-updating test suite for all 8 screens with full coverage (happy path + edge cases + visual regression + API/WebSocket validation), plus comprehensive backend unit and integration tests.

## Status: ✅ FULLY IMPLEMENTED

## Key Features
- **Self-Healing Selectors**: All tests use `data-testid` attributes
- **Visual Regression**: Screenshot comparison with dynamic content masking
- **Style & Accessibility Audits**: CSS validation and WCAG 2.1 AA compliance using axe-core
- **Maximized Browser Window**: All tests run in maximized window (`--start-maximized`)
- **Single Browser Window**: No flickering, login once with TOTP
- **Credential Storage**: Kite credentials stored locally (gitignored), auto-filled during login
- **Page Object Model**: Clean separation of selectors and actions
- **Backend Tests**: pytest-based unit, API, validation, and integration tests

---

## Test Count Summary (Actual)

### Frontend E2E Tests (Playwright)

| Screen | Happy | Edge | Visual | API/WS | Audit | Total |
|--------|-------|------|--------|--------|-------|-------|
| Login | 6 | 5 | 5 | 3 | 5 | **24** |
| Dashboard | 8 | 3 | 2 | - | 6 | **19** |
| Positions | 11 | 6 | 4 | 5 | 7 | **33** |
| Watchlist | 10 | 9 | 6 | 6 | 7 | **38** |
| Option Chain | 11 | 7 | 5 | 7 | 7 | **37** |
| Strategy Builder | 11 | 10 | 8 | 9 | 9 | **47** |
| Strategy Library | 25 | 20 | 15 | 20 | 9 | **89** |
| Integration | - | - | - | 3 | - | **3** |
| **Frontend Total** | **82** | **60** | **45** | **53** | **50** | **290** |

### Backend Tests (pytest)

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_strategy_templates.py` | ~15 | Model CRUD, constraints, JSON legs, defaults |
| `test_strategy_wizard_api.py` | ~35 | API endpoints: templates, wizard, deploy, compare |
| `test_strategy_validation.py` | ~15 | Legs config, strategy characteristics, win probs |
| `test_strategy_integration.py` | ~5 | Full flows, concurrent requests, mocked Kite |
| **Backend Total** | | **~70** |

### Grand Total: **~360 tests**

---

## Implementation Checklist

### Infrastructure ✅
- [x] Directory structure (fixtures, helpers, pages, specs, scripts)
- [x] `auth.fixture.js` - Token injection fixture + `auditablePage` fixture
- [x] `BasePage.js` - Base page object class with common methods
- [x] `visual.helper.js` - Screenshot masking utilities + viewport consistency
- [x] `style-audit.helper.js` - StyleAudit class with axe-core for accessibility
- [x] `generate-test.js` - Test scaffold generator
- [x] `kite-login.helper.js` - Automated Kite login (only TOTP manual)
- [x] `global-setup.js` - One-time login before all tests
- [x] `credentials.js` - Stored Kite credentials (gitignored)
- [x] Updated `playwright.config.js` for maximized browser window
- [x] Updated `package.json` with 25+ npm scripts

### Vue Components with data-testid ✅
- [x] `KiteHeader.vue` - 8 selectors (logo, nav items, user menu)
- [x] `LoginView.vue` - 4 selectors (page, buttons, error)
- [x] `DashboardView.vue` - 5 selectors (page, cards)
- [x] `PositionsView.vue` - 15 selectors (table, modals, buttons)
- [x] `WatchlistView.vue` - 18 selectors (search, tabs, instruments, modal)
- [x] `OptionChainView.vue` - 25 selectors (tabs, summary, table, selection)
- [x] `StrategyBuilderView.vue` - 28 selectors (toolbar, table, actions, summary)
- [x] `StrategyLibraryView.vue` - 40+ selectors (categories, cards, wizard, modals)

### Page Objects ✅
- [x] `BasePage.js` - Common navigation, selectors, assertions
- [x] `LoginPage.js` - Login button, error handling
- [x] `DashboardPage.js` - Navigation cards
- [x] `PositionsPage.js` - Table, modals, P&L display
- [x] `WatchlistPage.js` - Search, tabs, instruments, create modal
- [x] `OptionChainPage.js` - Underlying, expiry, strikes, selection
- [x] `StrategyBuilderPage.js` - Legs, calculations, summary cards
- [x] `StrategyLibraryPage.js` - Categories, wizard, cards, deploy modal

### Spec Files (35 files) ✅
- [x] Login: isolated (6), edge (5), visual (5), api (3), audit (5)
- [x] Dashboard: happy (8), edge (3), visual (2), audit (6)
- [x] Positions: happy (11), edge (6), visual (4), api (5), audit (7)
- [x] Watchlist: happy (10), edge (9), visual (6), websocket (6), audit (7)
- [x] Option Chain: happy (11), edge (7), visual (5), api (7), audit (7)
- [x] Strategy Builder: happy (11), edge (10), visual (8), api (9), audit (9)
- [x] Strategy Library: happy (25), edge (20), visual (15), api (20), audit (9)
- [x] Integration: oauth-full-flow (3)

### Backend Test Files ✅
- [x] `conftest.py` - Fixtures: db_session, mock templates, mock Kite client
- [x] `test_strategy_templates.py` - Model CRUD and constraints
- [x] `test_strategy_wizard_api.py` - All wizard API endpoints
- [x] `test_strategy_validation.py` - Legs config validation
- [x] `test_strategy_integration.py` - End-to-end flows

---

## Credential Storage & Authentication

### Setup (One-Time)
```
tests/config/
  credentials.js          # Your Kite User ID + Password (gitignored)
  credentials.example.js  # Template file (committed)
  .auth-token             # Saved JWT token (gitignored)
  .auth-state.json        # Browser state for reuse (gitignored)
```

### How It Works
1. **Global Setup** runs once before all tests
2. Checks if existing auth is valid (reuses if so)
3. If not valid, performs login:
   - Auto-fills User ID and Password from `credentials.js`
   - **Pauses 60 seconds for manual TOTP entry**
   - Saves token and browser state
4. All tests reuse the saved auth state
5. Token lasts ~8 hours before re-login needed

### Commands
```bash
# Run tests (login once, TOTP only)
npm test

# Force fresh login
rm tests/config/.auth-state.json && npm test

# Run specific test with shared auth
npm run test:specs:positions
```

---

## Single Browser Window Configuration

**File: `playwright.config.js`**
```javascript
export default defineConfig({
  workers: 1,              // Single worker = single browser
  fullyParallel: false,    // Sequential execution
  globalSetup: './tests/e2e/global-setup.js',  // Login once
  use: {
    storageState: './tests/config/.auth-state.json',  // Reuse auth
  },
  projects: [
    { name: 'setup', testMatch: /global-setup\.spec\.js/ },
    { name: 'chromium', dependencies: ['setup'], testIgnore: /.*\.isolated\.spec\.js/ },
    { name: 'isolated', testMatch: /.*\.isolated\.spec\.js/, use: { storageState: undefined } },
  ],
});
```

**Projects:**
- **chromium** - Main tests using saved auth state (single browser window)
- **isolated** - Tests needing fresh browser context (login page tests, OAuth tests)

**Benefits:**
- No browser flickering (one window throughout)
- Login happens once, not per-test
- Faster test execution
- Less load on Kite API
- Cleanup hooks prevent state pollution between tests

---

## Isolated Tests

Some tests require a fresh browser context without any saved authentication:
- **Login page tests** - Need to verify unauthenticated state
- **OAuth flow tests** - Need to test the full login flow

**File naming:** `*.isolated.spec.js`

**Running isolated tests:**
```bash
npm run test:isolated
```

**How it works:**
1. Tests matching `*.isolated.spec.js` are skipped by the main `chromium` project
2. They run in the `isolated` project with `storageState: undefined`
3. Each isolated test gets a fresh browser context

---

## Directory Structure

### Frontend Tests (Playwright)

```
tests/e2e/
  fixtures/
    auth.fixture.js              # Token injection fixture
    visual.fixture.js            # Visual regression setup
    strategy-library.fixture.js  # Strategy library mock data

  helpers/
    auth.helper.js               # EXISTING - Enhanced
    api.helper.js                # API validation helpers
    visual.helper.js             # Screenshot masking

  pages/
    BasePage.js                  # Base page object
    LoginPage.js
    DashboardPage.js
    WatchlistPage.js
    OptionChainPage.js
    StrategyBuilderPage.js
    StrategyLibraryPage.js       # NEW - Strategy Library POM
    PositionsPage.js
    components/
      KiteHeader.js
      Modals.js

  specs/
    login/
      login.isolated.spec.js   # Fresh browser context (no auth)
      login.edge.spec.js
      login.visual.spec.js
      login.api.spec.js
    dashboard/
      dashboard.happy.spec.js
      dashboard.edge.spec.js
      dashboard.visual.spec.js
    watchlist/
      watchlist.happy.spec.js
      watchlist.edge.spec.js
      watchlist.visual.spec.js
      watchlist.websocket.spec.js
    optionchain/
      optionchain.happy.spec.js
      optionchain.edge.spec.js
      optionchain.visual.spec.js
      optionchain.api.spec.js
    strategy/
      strategy.happy.spec.js
      strategy.edge.spec.js
      strategy.visual.spec.js
      strategy.api.spec.js
    strategylibrary/              # NEW - Strategy Library specs
      strategylibrary.happy.spec.js
      strategylibrary.edge.spec.js
      strategylibrary.visual.spec.js
      strategylibrary.api.spec.js
    positions/
      positions.happy.spec.js
      positions.edge.spec.js
      positions.visual.spec.js
      positions.api.spec.js
    integration/
      oauth-full-flow.spec.js
      optionchain-to-strategy.spec.js

  scripts/
    generate-test.js             # Test scaffold generator

  visual-baselines/              # Screenshot baselines
```

### Backend Tests (pytest)

```
backend/tests/
  __init__.py
  conftest.py                    # Fixtures: db_session, templates, mock Kite
  test_strategy_templates.py     # Model CRUD, constraints, JSON legs
  test_strategy_wizard_api.py    # All API endpoints
  test_strategy_validation.py    # Legs config, strategy characteristics
  test_strategy_integration.py   # Full flows, concurrent requests
```

---

## Implementation Phases

### Phase 1: Foundation (Priority: CRITICAL)

#### 1.1 Create Directory Structure
Create all directories as specified above.

#### 1.2 Implement Base Page Object
**File: `tests/e2e/pages/BasePage.js`**
```javascript
export class BasePage {
  constructor(page) {
    this.page = page;
  }

  async navigate(url) {
    await this.page.goto(url);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForSelector(selector, timeout = 10000) {
    await this.page.waitForSelector(selector, { timeout });
  }

  async screenshot(name) {
    await this.page.screenshot({ path: `tests/screenshots/${name}.png` });
  }
}
```

#### 1.3 Implement Auth Fixture
**File: `tests/e2e/fixtures/auth.fixture.js`**
- Token injection (bypass OAuth for most tests)
- Token validation via `/api/auth/me`
- Environment variable support (`TEST_AUTH_TOKEN`)
- Cached token reuse within session
- **Cleanup hooks** - Close modals and reset state after each test
- Fixtures: `authenticatedPage`, `auditablePage`, `styleAudit`

#### 1.4 Add data-testid to KiteHeader.vue
**File: `frontend/src/components/layout/KiteHeader.vue`**
```
data-testid="kite-header"
data-testid="kite-header-logo"
data-testid="kite-header-nav-dashboard"
data-testid="kite-header-nav-optionchain"
data-testid="kite-header-nav-strategy"
data-testid="kite-header-nav-watchlist"
data-testid="kite-header-nav-positions"
data-testid="kite-header-user-avatar"
```

---

### Phase 2: Page Objects

#### 2.1 Create Page Objects for Each Screen

| Page Object | File | Key Selectors |
|-------------|------|---------------|
| LoginPage | `pages/LoginPage.js` | `login-zerodha-button`, `login-error-message` |
| DashboardPage | `pages/DashboardPage.js` | `dashboard-watchlist-card`, `dashboard-strategy-card` |
| WatchlistPage | `pages/WatchlistPage.js` | `watchlist-search-input`, `watchlist-tabs`, `watchlist-instrument-row` |
| OptionChainPage | `pages/OptionChainPage.js` | `optionchain-underlying-tabs`, `optionchain-table`, `optionchain-strike-row-*` |
| StrategyBuilderPage | `pages/StrategyBuilderPage.js` | `strategy-add-row-button`, `strategy-leg-row-*`, `strategy-payoff-chart` |
| PositionsPage | `pages/PositionsPage.js` | `positions-table`, `positions-exit-button-*`, `positions-pnl-box` |

#### 2.2 Add data-testid to All Vue Components

**LoginView.vue:**
- `data-testid="login-page"`
- `data-testid="login-zerodha-button"`
- `data-testid="login-angelone-button"`
- `data-testid="login-error-message"`
- `data-testid="login-safety-toggle"`

**DashboardView.vue:**
- `data-testid="dashboard-page"`
- `data-testid="dashboard-watchlist-card"`
- `data-testid="dashboard-strategy-card"`
- `data-testid="dashboard-optionchain-card"`
- `data-testid="dashboard-positions-card"`

**WatchlistView.vue:**
- `data-testid="watchlist-page"`
- `data-testid="watchlist-search-input"`
- `data-testid="watchlist-tabs"`
- `data-testid="watchlist-instrument-row"`
- `data-testid="watchlist-create-modal"`
- `data-testid="watchlist-empty-state"`

**OptionChainView.vue:**
- `data-testid="optionchain-page"`
- `data-testid="optionchain-underlying-tabs"`
- `data-testid="optionchain-expiry-select"`
- `data-testid="optionchain-spot-price"`
- `data-testid="optionchain-table"`
- `data-testid="optionchain-strike-row-{strike}"`
- `data-testid="optionchain-ce-add-{strike}"`
- `data-testid="optionchain-pe-add-{strike}"`
- `data-testid="optionchain-add-to-strategy-button"`

**StrategyBuilderView.vue:**
- `data-testid="strategy-page"`
- `data-testid="strategy-underlying-tabs"`
- `data-testid="strategy-pnl-mode-toggle"`
- `data-testid="strategy-add-row-button"`
- `data-testid="strategy-leg-row-{index}"`
- `data-testid="strategy-payoff-chart"`
- `data-testid="strategy-summary-maxprofit"`
- `data-testid="strategy-save-button"`
- `data-testid="strategy-share-button"`

**PositionsView.vue:**
- `data-testid="positions-page"`
- `data-testid="positions-day-button"`
- `data-testid="positions-net-button"`
- `data-testid="positions-pnl-box"`
- `data-testid="positions-table"`
- `data-testid="positions-exit-button-{symbol}"`
- `data-testid="positions-add-button-{symbol}"`
- `data-testid="positions-exit-modal"`
- `data-testid="positions-empty-state"`

---

### Phase 3: Test Coverage

#### 3.1 Test Matrix Per Screen

| Screen | Happy Path | Edge Cases | Visual | API |
|--------|------------|------------|--------|-----|
| Login | 6 tests | 5 tests | 5 tests | 3 tests |
| Dashboard | 8 tests | 3 tests | 2 tests | - |
| Watchlist | 8 tests | 4 tests | 3 tests | 4 tests |
| OptionChain | 13 tests | 6 tests | 4 tests | 4 tests |
| StrategyBuilder | 15 tests | 7 tests | 4 tests | 5 tests |
| Positions | 11 tests | 6 tests | 4 tests | 4 tests |
| **TOTAL** | **61** | **31** | **22** | **20** |

#### 3.2 Happy Path Tests (61 tests)

**Login (6):** page loads, Zerodha default, features display, OAuth initiation, safety toggle, Angel One message
**Dashboard (8):** page loads, 4 cards visible, each card navigates correctly, header visible, user avatar
**Watchlist (8):** page loads, tabs visible, search works, add instrument, remove instrument, create watchlist, switch tabs, live prices
**OptionChain (13):** page loads, underlying tabs, switch underlying, expiry dropdown, spot price, DTE, table loads, ATM highlight, OI bars, Greeks toggle, select CE/PE, navigate to Strategy
**StrategyBuilder (15):** page loads, underlying selector, P/L mode, add leg, select expiry/strike, entry price, P/L grid, breakeven columns, summary cards, payoff chart, save/load/share strategy
**Positions (11):** page loads, Day/Net toggle, P/L box, summary bar, table loads, Exit/Add buttons, Exit/Add modals, auto-refresh

#### 3.3 Edge Case Tests (31 tests)

**Login (5):** OAuth failure, unauthenticated redirect, network error, loading state, Angel One coming soon
**Dashboard (3):** auth guard, expired token, responsive layout
**Watchlist (4):** empty state, no search results, 100 instrument limit, WebSocket disconnect
**OptionChain (6):** empty chain, loading state, error state, strikes range change, clear selection, expired options
**StrategyBuilder (7):** empty state, delete legs, missing entry price, no internet, grid columns limit, horizontal scroll, no browser overflow
**Positions (6):** empty state, link to Option Chain, loading state, Exit All confirmation, cancel Exit All, Market/Limit toggle

#### 3.4 Visual Regression Tests (22 tests)

Each screen at: 1920x1080, 1440x900, 1024x768 + key states (empty, populated, error, modal open)

**Dynamic Content Masking:**
```javascript
// Mask prices, timestamps, OI, IV before screenshot
await page.evaluate(() => {
  document.querySelectorAll('[data-testid*="ltp"], .ltp, .price').forEach(el => {
    el.textContent = '00,000.00';
  });
  document.querySelectorAll('[data-testid*="pnl"], .pnl').forEach(el => {
    el.textContent = '+0,000';
  });
});
```

#### 3.5 API Validation Tests (20 tests)

**Login:** `/api/auth/zerodha/login` returns URL
**Watchlist:** CRUD endpoints, search endpoint
**OptionChain:** `/api/optionchain/chain`, `/api/optionchain/oi-analysis`
**Strategy:** `/api/strategies/calculate`, CRUD endpoints, share endpoint
**Positions:** `/api/positions/`, exit/add/exit-all endpoints

---

### Phase 4: Test Generator Script

**File: `tests/e2e/scripts/generate-test.js`**

```bash
# Usage
npm run generate:test -- --screen MyNewScreen --path /mynewscreen

# Generates:
# - pages/MyNewScreenPage.js (Page Object)
# - specs/mynewscreen/mynewscreen.happy.spec.js
# - specs/mynewscreen/mynewscreen.edge.spec.js
# - specs/mynewscreen/mynewscreen.visual.spec.js
# - specs/mynewscreen/mynewscreen.api.spec.js
```

---

### Phase 5: NPM Scripts

**Add to package.json:**
```json
{
  "test:login": "playwright test specs/login/",
  "test:dashboard": "playwright test specs/dashboard/",
  "test:watchlist": "playwright test specs/watchlist/",
  "test:optionchain": "playwright test specs/optionchain/",
  "test:strategy": "playwright test specs/strategy/",
  "test:positions": "playwright test specs/positions/",

  "test:happy": "playwright test --grep happy",
  "test:edge": "playwright test --grep edge",
  "test:visual": "playwright test --grep visual",
  "test:api": "playwright test --grep api",

  "test:visual:update": "playwright test --grep visual --update-snapshots",

  "generate:test": "node tests/e2e/scripts/generate-test.js"
}
```

---

## Files to Create/Modify

### New Files (23 files)
1. `tests/e2e/fixtures/auth.fixture.js`
2. `tests/e2e/fixtures/visual.fixture.js`
3. `tests/e2e/helpers/api.helper.js`
4. `tests/e2e/helpers/visual.helper.js`
5. `tests/e2e/pages/BasePage.js`
6. `tests/e2e/pages/LoginPage.js`
7. `tests/e2e/pages/DashboardPage.js`
8. `tests/e2e/pages/WatchlistPage.js`
9. `tests/e2e/pages/OptionChainPage.js`
10. `tests/e2e/pages/StrategyBuilderPage.js`
11. `tests/e2e/pages/PositionsPage.js`
12. `tests/e2e/pages/components/KiteHeader.js`
13. `tests/e2e/pages/components/Modals.js`
14. `tests/e2e/scripts/generate-test.js`
15-28. Spec files (14 spec files across 6 screens)

### Modify Files (8 files)
1. `frontend/src/components/layout/KiteHeader.vue` - Add data-testid
2. `frontend/src/views/LoginView.vue` - Add data-testid
3. `frontend/src/views/DashboardView.vue` - Add data-testid
4. `frontend/src/views/WatchlistView.vue` - Add data-testid
5. `frontend/src/views/OptionChainView.vue` - Add data-testid
6. `frontend/src/views/StrategyBuilderView.vue` - Add data-testid
7. `frontend/src/views/PositionsView.vue` - Add data-testid
8. `package.json` - Add npm scripts

### Existing Tests to Keep
Keep all 16 existing test files in `tests/e2e/` as reference/fallback until new tests are validated.

---

## Implementation Order

| Priority | Task | Estimated Effort |
|----------|------|------------------|
| 1 | Create directory structure | 15 min |
| 2 | Implement auth.fixture.js | 1 hour |
| 3 | Implement BasePage.js | 30 min |
| 4 | Add data-testid to KiteHeader.vue | 30 min |
| 5 | Add data-testid to all Vue views | 2 hours |
| 6 | Create all Page Objects (6 files) | 3 hours |
| 7 | Create happy path tests | 4 hours |
| 8 | Create edge case tests | 3 hours |
| 9 | Create visual.helper.js | 1 hour |
| 10 | Create visual regression tests | 2 hours |
| 11 | Create API validation tests | 2 hours |
| 12 | Create generate-test.js script | 2 hours |
| 13 | Update package.json scripts | 15 min |
| 14 | Update CLAUDE.md documentation | 30 min |

**Total Estimated Effort: ~22 hours**

---

## Success Criteria

1. All 134 tests pass (61 happy + 31 edge + 22 visual + 20 API)
2. Visual baselines generated for all screens
3. Test generator creates valid scaffolds
4. Token injection bypasses OAuth for 95% of tests
5. No horizontal overflow at any viewport
6. All data-testid attributes in place
7. npm scripts work correctly

---

## Running Tests

### Frontend E2E Tests (Playwright)

```bash
# Run all tests for a specific screen
npm run test:specs:login
npm run test:specs:dashboard
npm run test:specs:watchlist
npm run test:specs:optionchain
npm run test:specs:strategy
npm run test:specs:positions
npm run test:specs:strategylibrary   # NEW

# Run tests by type
npm run test:happy        # All happy path tests (@happy)
npm run test:edge         # All edge case tests (@edge)
npm run test:visual       # All visual regression tests (@visual)
npm run test:api:new      # All API validation tests (@api)
npm run test:audit        # All style & accessibility audits (@audit)
npm run test:isolated     # Tests needing fresh browser context (login, OAuth)

# Update visual baselines
npm run test:visual:update

# Run with visible browser
npx playwright test tests/e2e/specs/strategylibrary/ --headed

# Generate tests for new screen
npm run generate:test -- --screen MyNewScreen --path /mynewscreen
```

### Backend Tests (pytest)

```bash
cd backend

# Run all strategy tests
pytest tests/test_strategy*.py -v

# Run individual test files
pytest tests/test_strategy_templates.py -v      # Model tests
pytest tests/test_strategy_wizard_api.py -v     # API endpoint tests
pytest tests/test_strategy_validation.py -v     # Validation tests
pytest tests/test_strategy_integration.py -v    # Integration tests

# Run with coverage
pytest tests/test_strategy*.py -v \
  --cov=app/api/routes/strategy_wizard \
  --cov=app/models/strategy_templates

# Run with HTML report
pytest tests/test_strategy*.py -v --html=reports/strategy-tests.html

# Run specific test by name
pytest tests/test_strategy_wizard_api.py::TestWizard::test_wizard_returns_top_5 -v
```
