# AlgoChanakya Architectural Rules

**Purpose:** Consolidated architectural rules enforced by code-reviewer agent and hooks.
**Last Updated:** 2026-02-17
**Status:** Protected file - changes require review

This document consolidates all critical architectural rules from CLAUDE.md, backend/CLAUDE.md, frontend/CLAUDE.md, and agent definitions.

---

## Table of Contents

1. [Folder Structure Rules](#folder-structure-rules)
2. [Cross-Layer Import Rules](#cross-layer-import-rules)
3. [Broker Abstraction Rules](#broker-abstraction-rules)
4. [Trading Constants Rules](#trading-constants-rules)
5. [Protected Files](#protected-files)
6. [Security Rules](#security-rules)
7. [Testing Rules](#testing-rules)
8. [Database Patterns](#database-patterns)
9. [Naming Conventions](#naming-conventions)

---

## Folder Structure Rules

**Enforcement:** PreToolUse hooks (`guard_folder_structure.py`)

### Backend Services (`backend/app/services/`)

**Allowed at root:**
- `__init__.py` (package initializer)
- `instruments.py` (legacy instrument service)
- `ofo_calculator.py` (legacy OFO calculator)
- `option_chain_service.py` (legacy option chain service)

**All other services MUST be in subdirectories:**
- `autopilot/` - AutoPilot strategy engine, conditions, adjustments
- `options/` - Options pricing, Greeks, strike selection
- `legacy/` - Legacy watchlist, positions services
- `ai/` - AI regime detection, risk scoring, recommendations
- `brokers/` - Broker adapters and market data abstractions

❌ **Violations:**
```
backend/app/services/new_service.py          # BLOCKED: Root not allowed
backend/app/services/strategy_builder.py     # BLOCKED: Must be in autopilot/
```

✅ **Correct:**
```
backend/app/services/autopilot/strategy_builder.py
backend/app/services/options/strike_selector.py
backend/app/services/brokers/angel/smartapi_adapter.py
```

### Frontend Assets (`frontend/src/assets/`)

**Required structure:**
- `styles/` - ALL CSS files (NOT `css/`)
- `logos/` - ALL image files (PNG, JPG, SVG)

❌ **Violations:**
```
frontend/src/assets/css/styles.css      # BLOCKED: Must be in styles/
frontend/src/assets/logo.png            # BLOCKED: Must be in logos/
```

✅ **Correct:**
```
frontend/src/assets/styles/dashboard.css
frontend/src/assets/logos/kite-logo.png
```

### Frontend API Code (`frontend/src/services/`)

ALL API calls MUST use:
- `src/services/api.js` - Axios instance with interceptors
- `src/services/{module}Api.js` - Feature-specific API modules

❌ **Violations:**
```javascript
// BLOCKED: Direct axios import
import axios from 'axios'
const response = await axios.get('/api/positions')
```

✅ **Correct:**
```javascript
import api from '@/services/api'
const response = await api.get('/positions')
```

### Test Files

**E2E tests:** `tests/e2e/specs/{screen}/`
- MUST be in screen subdirectory (dashboard/, positions/, strategy/, etc.)
- File naming: `{feature}.spec.js`

**Backend tests:** `tests/backend/{module}/`
- MUST be in module subdirectory (autopilot/, options/, brokers/, etc.)
- File naming: `test_{module}.py`

❌ **Violations:**
```
tests/e2e/specs/dashboard.spec.js        # BLOCKED: No subdirectory
tests/backend/test_autopilot.py          # BLOCKED: No subdirectory
```

✅ **Correct:**
```
tests/e2e/specs/dashboard/positions-display.spec.js
tests/backend/autopilot/test_strategy_engine.py
```

---

## Cross-Layer Import Rules

**Enforcement:** PreToolUse hooks (`guard_cross_feature_imports.py`) + CI (`validate-cross-imports.py`)

### Rule 1: Backend Cannot Import from Frontend

**NEVER import frontend code from backend Python files.**

❌ **Violations:**
```python
# BLOCKED: Backend importing from frontend
from frontend.src.services import api
from frontend.components import MyComponent
import frontend.utils
```

✅ **Correct:**
```python
# Backend should only import from:
from app.models import User
from app.services.brokers import get_broker_adapter
from app.utils.encryption import encrypt_field
import asyncio
import re
```

**Why:** Backend is a separate layer that runs on the server. It cannot access frontend code (which runs in the browser). Use API endpoints for communication.

### Rule 2: Frontend Cannot Import from Backend

**NEVER import backend code from frontend JavaScript/Vue files.**

❌ **Violations:**
```javascript
// BLOCKED: Frontend importing from backend
import { get_broker_adapter } from 'backend/app/services/brokers/factory'
import { User } from 'app.models'
from '../backend/app/services/autopilot/strategy_engine'
```

✅ **Correct:**
```javascript
// Frontend should use API calls instead:
import api from '@/services/api'
import { positionsApi } from '@/services/positionsApi'

// Fetch data via API
const positions = await positionsApi.getAll()
```

**Why:** Frontend runs in the browser and cannot directly access backend Python code. All backend communication MUST go through API endpoints.

### Rule 3: Tests Can Import from Both Layers

**Test files are exempt** from cross-layer import restrictions.

✅ **Allowed in tests:**
```javascript
// E2E tests can import from both layers
import { test, expect } from '../../config/auth.fixture.js'
import { authenticatedPage } from '@/test/fixtures'
```

```python
# Backend tests can import from app modules
from app.models import User, Position
from app.services.brokers.factory import get_broker_adapter
```

**Why:** Tests need to access both layers to verify integration and functionality.

### Enforcement in CI

**CI workflows validate cross-layer imports:**
- `.github/workflows/hook-parity.yml` - Standalone hook parity checks
- `.github/workflows/backend-tests.yml` - Includes cross-import validation step

**Script:** `.github/scripts/validate-cross-imports.py` mirrors the local hook logic.

---

## Broker Abstraction Rules

**Enforcement:** Code-reviewer agent (critical severity)
**SSOT:** [docs/architecture/broker-abstraction.md](../docs/architecture/broker-abstraction.md) for full architecture. Code examples below are quick reference.

### Rule 1: Never Use Broker-Specific APIs Directly

**NEVER directly import or use:**
- `KiteConnect` (Zerodha)
- `SmartConnect` / `SmartApi` (AngelOne)
- Any broker's SDK classes

**ALWAYS use:**
- Broker adapters via factory functions
- Unified data models (`UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`)

❌ **Violations:**
```python
# BLOCKED: Direct KiteConnect usage
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=API_KEY)
orders = kite.orders()

# BLOCKED: Direct SmartAPI usage
from SmartApi import SmartConnect
obj = SmartConnect(api_key=API_KEY)
data = obj.getProfile()
```

✅ **Correct:**
```python
# Order execution via adapter
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter(user.order_broker_type, credentials)
orders = await adapter.get_orders()  # Returns List[UnifiedOrder]

# Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote
```

### Rule 2: Use Canonical Symbol Format

**Internal representation:** ALL symbols MUST use canonical format (Kite format):
- `NSE:NIFTY24FEB24000CE` (options)
- `NSE:INFY` (equity)

**Broker-specific symbols:** Use `SymbolConverter` for broker APIs:
```python
from app.utils.symbol_converter import SymbolConverter

# Convert canonical to broker-specific
broker_symbol = SymbolConverter.to_broker_format(canonical_symbol, broker_type)

# Convert broker-specific to canonical
canonical_symbol = SymbolConverter.to_canonical_format(broker_symbol, broker_type)
```

### Rule 3: Unified Data Models

**ALWAYS return unified models from broker operations:**

```python
# Unified models (app/services/brokers/models.py)
@dataclass
class UnifiedOrder:
    order_id: str
    symbol: str  # Canonical format
    transaction_type: str  # "BUY" or "SELL"
    quantity: int
    price: float
    status: str  # "OPEN", "COMPLETE", "REJECTED", "CANCELLED"
    broker_type: str  # "kite", "angel", etc.

@dataclass
class UnifiedPosition:
    symbol: str  # Canonical format
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    broker_type: str

@dataclass
class UnifiedQuote:
    symbol: str  # Canonical format
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    broker_type: str
```

---

## Trading Constants Rules

**Enforcement:** Code-reviewer agent (critical severity) + `trading-constants-manager` skill

### Rule: Never Hardcode Trading Parameters

**NEVER hardcode:**
- Lot sizes
- Strike steps (intervals)
- Index tokens
- Expiry patterns
- Any trading-related constants

❌ **Violations:**
```python
# BLOCKED: Hardcoded lot size
lot_size = 25  # NIFTY lot size

# BLOCKED: Hardcoded strike step
strike_step = 50  # NIFTY strike step

# BLOCKED: Hardcoded index token
nifty_token = 256265
```

✅ **Correct (Backend):**
```python
from app.constants.trading import get_lot_size, get_strike_step, INDEX_TOKENS

lot_size = get_lot_size("NIFTY")  # 25
strike_step = get_strike_step("NIFTY")  # 50
nifty_token = INDEX_TOKENS["NIFTY"]  # 256265
```

✅ **Correct (Frontend):**
```javascript
import { getLotSize, getStrikeStep, INDEX_TOKENS } from '@/constants/trading'

const lotSize = getLotSize('NIFTY')  // 25
const strikeStep = getStrikeStep('NIFTY')  // 50
const niftyToken = INDEX_TOKENS.NIFTY  // 256265
```

**Why:** Index parameters change (NIFTY lot size was 50, now 25). Centralized constants ensure consistency and easy updates.

---

## Protected Files

**Enforcement:** PreToolUse hooks (`protect_sensitive_files.py`)

### Read/Write/Edit Blocked Files

**NEVER access these files/patterns:**

| Pattern | Reason | Allowed Tools |
|---------|--------|---------------|
| `**/.env*` | Environment credentials | None (manual edit only) |
| `C:\Apps\algochanakya/**` | Production folder | **ABSOLUTELY NONE** |
| `**/knowledge.db` | Learning database | Hook-managed |
| `**/workflow-state.json` | Hook-managed state | Hook-managed |
| `**/.auth-state.json` | Test credentials | Playwright only |
| `**/.auth-token` | Test tokens | Playwright only |

**Production folder rule:** `C:\Apps\algochanakya` is the production instance running on the same machine. NEVER:
- Read, modify, or copy files
- Kill, restart, or interfere with processes
- Run commands affecting this folder
- Reference this path in any tool call

**Development folder:** `C:\Abhay\VideCoding\algochanakya` - Work ONLY here.

---

## Security Rules

**Enforcement:** Code-reviewer agent (high severity)

### Rule 1: Never Commit Secrets

**NEVER commit:**
- API keys, access tokens, client secrets
- Database passwords
- Encryption keys
- Broker credentials (TOTP secrets, API keys)

**Use:**
- `.env` files (ignored by git)
- `app/utils/encryption.py` for encrypted database storage
- Environment variables for CI/CD

### Rule 2: Encrypt Sensitive Database Fields

**Required encryption:**
```python
from app.utils.encryption import encrypt_field, decrypt_field

# Storing
encrypted_totp = encrypt_field(totp_secret)
cred.totp_secret = encrypted_totp

# Retrieving
totp_secret = decrypt_field(cred.totp_secret)
```

**Fields requiring encryption:**
- `totp_secret` (SmartAPI TOTP)
- `api_key`, `client_secret` (all brokers)
- `access_token`, `refresh_token` (OAuth tokens)

### Rule 3: Validate User Input

**ALWAYS validate:**
- Strike prices (must be valid for symbol)
- Quantities (must be multiples of lot size)
- Order types (BUY, SELL, LIMIT, MARKET)
- Symbol formats (reject invalid formats)

```python
# Example validation
from app.constants.trading import get_lot_size

def validate_quantity(symbol: str, quantity: int):
    lot_size = get_lot_size(symbol.split(':')[0])  # Extract index
    if quantity % lot_size != 0:
        raise ValueError(f"Quantity must be multiple of {lot_size}")
```

---

## Testing Rules

**Enforcement:** Code-reviewer agent (high severity) + E2E test hooks

### E2E Test Rules (CRITICAL)

**SSOT:** [docs/testing/e2e-test-rules.md](../docs/testing/e2e-test-rules.md) for complete guidelines. Quick reference below.

**1. Use `data-testid` ONLY - no CSS classes, tags, or text selectors**

❌ **Violations:**
```javascript
// BLOCKED: CSS class selector
await page.locator('.exit-button').click()

// BLOCKED: Tag selector
await page.locator('button').click()

// BLOCKED: Text selector
await page.getByText('Exit All').click()
```

✅ **Correct:**
```javascript
// data-testid only
await page.getByTestId('positions-exit-all-button').click()
```

**2. Import from `auth.fixture.js` (NOT `@playwright/test`)**

❌ **Violation:**
```javascript
import { test, expect } from '@playwright/test'
```

✅ **Correct:**
```javascript
import { test, expect } from '../../config/auth.fixture.js'
```

**3. Use `authenticatedPage` fixture for authenticated tests**

```javascript
test('should display positions', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/positions')
  await expect(authenticatedPage.getByTestId('positions-table')).toBeVisible()
})
```

**4. data-testid naming convention: `[screen]-[component]-[element]`**

```html
<!-- Correct naming -->
<button data-testid="positions-exit-modal">Exit</button>
<input data-testid="strategy-lots-input" />
<div data-testid="dashboard-pnl-card"></div>
```

### Backend Test Rules

**1. Use async fixtures**

```python
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_positions(client):
    response = await client.get("/positions")
    assert response.status_code == 200
```

**2. Mock external broker APIs**

```python
@pytest.fixture
def mock_kite_adapter(mocker):
    mock = mocker.patch('app.services.brokers.factory.get_broker_adapter')
    mock.return_value.get_positions.return_value = [
        UnifiedPosition(symbol="NSE:INFY", quantity=25, ...)
    ]
    return mock
```

---

## Database Patterns

### Adding New Models

**Checklist:**
1. Create model in `backend/app/models/{module}.py`
2. Import in `backend/app/models/__init__.py`
3. Import in `backend/alembic/env.py` (required for autogenerate)
4. Run migration: `alembic revision --autogenerate -m "description" && alembic upgrade head`

### Async Database Operations (CRITICAL)

**ALL SQLAlchemy operations MUST use async/await:**

❌ **Violation:**
```python
# BLOCKED: Sync database operation
user = db.query(User).filter(User.id == user_id).first()
```

✅ **Correct:**
```python
# Async database operation
from sqlalchemy import select

result = await db.execute(select(User).filter(User.id == user_id))
user = result.scalar_one_or_none()
```

### Database Session Management

**Use dependency injection:**
```python
from app.database import get_db

@router.get("/positions")
async def get_positions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Position))
    return result.scalars().all()
```

---

## Naming Conventions

### Backend (Python)

- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private methods:** `_leading_underscore`

```python
# File: strategy_engine.py
class StrategyEngine:
    MAX_POSITIONS = 10  # Constant

    def execute_strategy(self):  # Public method
        self._validate_inputs()  # Private method
```

### Frontend (JavaScript/Vue)

- **Files:** `kebab-case.vue`, `camelCase.js`
- **Components:** `PascalCase.vue`
- **Variables:** `camelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Composables:** `use{Name}.js`

```javascript
// File: usePositions.js
export function usePositions() {
  const MAX_RETRIES = 3  // Constant
  const positionsList = ref([])  // Variable

  function fetchPositions() { ... }

  return { positionsList, fetchPositions }
}
```

### data-testid Naming

**Format:** `{screen}-{component}-{element}`

```html
<!-- Dashboard screen, PNL card, value element -->
<span data-testid="dashboard-pnl-value">+5000</span>

<!-- Strategy screen, lots input -->
<input data-testid="strategy-lots-input" />

<!-- Positions screen, exit all button -->
<button data-testid="positions-exit-all-button">Exit All</button>
```

---

## Enforcement Summary

| Rule Category | Enforced By | Severity | Blocking |
|--------------|-------------|----------|----------|
| Folder structure | `guard_folder_structure.py` hook | High | Yes (PreToolUse) |
| Cross-layer imports | `guard_cross_feature_imports.py` hook | High | Yes (PreToolUse) |
| Protected files | `protect_sensitive_files.py` hook | Critical | Yes (PreToolUse) |
| Broker abstraction | `code-reviewer` agent | Critical | Yes (review gate) |
| Trading constants | `code-reviewer` agent + skill | Critical | Yes (review gate) |
| Security | `code-reviewer` agent | High | Yes (review gate) |
| Testing (data-testid) | `code-reviewer` agent | High | Yes (review gate) |
| Database patterns | `code-reviewer` agent | Medium | Warning only |
| Naming conventions | `code-reviewer` agent | Low | Warning only |

**Review process:** All fixes pass through `code-reviewer` agent before applying. Hook violations block tool execution immediately.

---

**References:**
- [CLAUDE.md](../CLAUDE.md) - Project instructions
- [backend/CLAUDE.md](../backend/CLAUDE.md) - Backend patterns
- [frontend/CLAUDE.md](../frontend/CLAUDE.md) - Frontend patterns
- [Broker Abstraction Architecture](../docs/architecture/broker-abstraction.md)
- [code-reviewer agent](agents/code-reviewer.md)
