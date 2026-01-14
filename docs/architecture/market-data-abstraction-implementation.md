# Market Data Broker Abstraction - Part 3: Implementation Guide

> **Part of:** Multi-Broker Market Data Abstraction
> **Version:** 2.0
> **Status:** Complete Implementation Guide
> **Related Files:**
> - [Part 1: Design & Specification](./market-data-abstraction-design.md)
> - [Part 2: Code Specifications](./market-data-abstraction-code-specs.md)

---

## Table of Contents

12. [Frontend Implementation](#12-frontend-implementation)
13. [Backend API Endpoints](#13-backend-api-endpoints)
14. [Implementation Roadmap](#14-implementation-roadmap)

---

## 12. FRONTEND IMPLEMENTATION

### 12.1 Settings UI Component

**File:** `frontend/src/views/SettingsView.vue`

Add broker selection section:

```vue
<template>
  <div class="settings-container">
    <!-- Existing settings sections -->

    <!-- Market Data Source Selection -->
    <div class="setting-section" data-testid="settings-market-data-section">
      <h3>Market Data Source</h3>
      <p class="setting-description">
        Choose which broker provides live prices, option chain data, and historical OHLCV.
        This is independent of your order execution broker.
      </p>

      <div class="setting-group">
        <label for="market-data-broker">Data Provider</label>
        <select
          id="market-data-broker"
          v-model="settings.market_data_broker"
          @change="handleBrokerChange"
          data-testid="settings-market-data-broker-select"
        >
          <option value="smartapi">Angel One (SmartAPI) - FREE [Default]</option>
          <option value="kite">Zerodha (Kite Connect) - ₹500/month</option>
          <option value="upstox">Upstox - FREE</option>
          <option value="dhan">Dhan - FREE (25 F&O trades/mo) or ₹499/mo</option>
          <option value="fyers">Fyers - FREE</option>
          <option value="paytm">Paytm Money - FREE</option>
        </select>

        <div class="broker-info" v-if="brokerInfo[settings.market_data_broker]">
          <p>{{ brokerInfo[settings.market_data_broker].description }}</p>
          <a :href="brokerInfo[settings.market_data_broker].link" target="_blank">
            Learn more →
          </a>
        </div>
      </div>

      <div class="setting-actions">
        <button
          @click="testConnection"
          :disabled="testing"
          data-testid="settings-test-connection-button"
          class="btn btn-secondary"
        >
          <span v-if="!testing">Test Connection</span>
          <span v-else>Testing...</span>
        </button>

        <button
          @click="saveSettings"
          :disabled="saving"
          data-testid="settings-save-button"
          class="btn btn-primary"
        >
          Save Changes
        </button>
      </div>

      <div
        v-if="connectionStatus"
        :class="['connection-status', connectionStatus.type]"
        data-testid="settings-connection-status"
      >
        <span class="status-icon">{{ connectionStatus.icon }}</span>
        <span>{{ connectionStatus.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { brokerAPI } from '@/services/api'

const { showToast } = useToast()

const settings = reactive({
  market_data_broker: 'smartapi',
  // ... other settings
})

const testing = ref(false)
const saving = ref(false)
const connectionStatus = ref(null)

const brokerInfo = {
  smartapi: {
    description: 'Angel One SmartAPI provides free WebSocket and REST APIs with auto-TOTP authentication.',
    link: 'https://smartapi.angelbroking.com/'
  },
  kite: {
    description: 'Zerodha Kite Connect requires ₹500/month subscription but offers robust APIs.',
    link: 'https://kite.trade/docs/connect/v3/'
  },
  upstox: {
    description: 'Upstox provides free market data APIs with WebSocket support.',
    link: 'https://upstox.com/developer/'
  },
  dhan: {
    description: 'Dhan offers free data APIs if you execute 25 F&O trades/month, otherwise ₹499/mo.',
    link: 'https://dhanhq.co/docs'
  },
  fyers: {
    description: 'Fyers provides free market data APIs with good documentation.',
    link: 'https://myapi.fyers.in/docsv3'
  },
  paytm: {
    description: 'Paytm Money offers free APIs for live prices and historical data.',
    link: 'https://developer.paytmmoney.com/'
  }
}

async function testConnection() {
  testing.value = true
  connectionStatus.value = null

  try {
    const response = await brokerAPI.testConnection(settings.market_data_broker)

    connectionStatus.value = {
      type: 'success',
      icon: '✓',
      message: `Connected successfully to ${settings.market_data_broker}`
    }

    showToast('Connection test successful', 'success')
  } catch (error) {
    connectionStatus.value = {
      type: 'error',
      icon: '✗',
      message: error.response?.data?.detail || 'Connection failed'
    }

    showToast('Connection test failed', 'error')
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true

  try {
    await brokerAPI.updateMarketDataBroker(settings.market_data_broker)
    showToast('Settings saved successfully', 'success')

    // Refresh WebSocket connection with new broker
    window.location.reload()
  } catch (error) {
    showToast('Failed to save settings', 'error')
  } finally {
    saving.value = false
  }
}

function handleBrokerChange() {
  connectionStatus.value = null
}

onMounted(async () => {
  // Load current settings
  // ... existing code
})
</script>

<style scoped>
.setting-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.broker-info {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: var(--info-bg);
  border-radius: 4px;
  font-size: 0.9rem;
}

.connection-status {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.connection-status.success {
  background: var(--success-bg);
  color: var(--success-text);
}

.connection-status.error {
  background: var(--error-bg);
  color: var(--error-text);
}

.setting-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}
</style>
```

### 12.2 API Client Updates

**File:** `frontend/src/services/api.js`

Add broker management endpoints:

```javascript
// Market Data Broker Management
export const brokerAPI = {
  // Update user's market data broker preference
  updateMarketDataBroker: (broker) =>
    api.put('/user/preferences', { market_data_broker: broker }),

  // Test connection to broker
  testConnection: (broker) =>
    api.post('/market-data/test-connection', { broker }),

  // Get broker credentials (if stored)
  getBrokerCredentials: (broker) =>
    api.get(`/brokers/${broker}/credentials`),

  // Save broker credentials
  saveBrokerCredentials: (broker, credentials) =>
    api.post(`/brokers/${broker}/credentials`, credentials),

  // Delete broker credentials
  deleteBrokerCredentials: (broker) =>
    api.delete(`/brokers/${broker}/credentials`),
}
```

---

## 13. BACKEND API ENDPOINTS

**File:** `backend/app/api/routes/market_data.py`

```python
"""
Market Data Broker Management API

Endpoints for managing market data broker selection and configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database import get_db
from app.models import User, UserPreferences
from app.utils.dependencies import get_current_user
from app.services.brokers.market_data_factory import get_market_data_adapter
from app.services.brokers.exceptions import BrokerAPIError, BrokerAuthenticationError

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.post("/test-connection")
async def test_connection(
    broker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Test connection to market data broker.

    Args:
        broker: Broker identifier (smartapi, kite, upstox, etc.)
        user: Current user
        db: Database session

    Returns:
        Connection status and broker info

    Raises:
        HTTPException: If connection fails
    """
    try:
        # Get adapter for broker
        adapter = await get_market_data_adapter(broker, user.id, db)

        # Test connection by fetching NIFTY 50 quote
        quotes = await adapter.get_ltp(["NIFTY 50"])

        return {
            "status": "success",
            "broker": broker,
            "message": f"Successfully connected to {broker}",
            "test_quote": {
                "symbol": "NIFTY 50",
                "ltp": str(quotes.get("NIFTY 50", 0))
            }
        }

    except BrokerAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
    except BrokerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Broker API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


@router.put("/switch-broker")
async def switch_broker(
    new_broker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Switch user's market data broker.

    Args:
        new_broker: New broker identifier
        user: Current user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If broker switch fails
    """
    # Validate broker
    valid_brokers = ['smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm']
    if new_broker not in valid_brokers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker. Must be one of: {', '.join(valid_brokers)}"
        )

    try:
        # Get or create user preferences
        prefs = await db.get(UserPreferences, user.id)
        if not prefs:
            prefs = UserPreferences(user_id=user.id)
            db.add(prefs)

        # Update broker
        prefs.market_data_source = new_broker
        await db.commit()

        return {
            "status": "success",
            "message": f"Market data broker switched to {new_broker}",
            "broker": new_broker
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch broker: {str(e)}"
        )


@router.get("/current-broker")
async def get_current_broker(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Get user's current market data broker."""
    prefs = await db.get(UserPreferences, user.id)

    return {
        "broker": prefs.market_data_source if prefs else "smartapi",
        "default": "smartapi"
    }
```

**Register in `backend/app/main.py`:**
```python
from app.api.routes import market_data

app.include_router(market_data.router)
```

---

## 14. IMPLEMENTATION ROADMAP

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Build foundation - interfaces, base classes, database schema

**Tasks:**
1. ✅ Create `market_data_base.py` with all dataclasses
   - `MarketDataBrokerType` enum
   - `BrokerCredentials` and subclasses
   - `OHLCVCandle` dataclass
   - `Instrument` dataclass

2. ✅ Create `ticker_base.py` with `TickerService` interface

3. ✅ Create `symbol_converter.py` with `CanonicalSymbol` and `SymbolConverter`
   - Implement parsers for all 6 brokers
   - Add unit tests for each broker format

4. ✅ Create database tables
   - `broker_instrument_tokens` table
   - Update `user_preferences` (add all 6 brokers to enum/constraint)
   - Create credential tables for new brokers

5. ✅ Run migrations
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add market data abstraction tables"
   alembic upgrade head
   ```

6. ✅ Create error handling classes (`exceptions.py`)

7. ✅ Create `rate_limiter.py` and `token_manager.py`

**Deliverables:**
- All base interfaces defined
- Database schema complete
- Unit tests passing (symbol conversion, rate limiting)

---

### Phase 2: SmartAPI Adapter (Week 2)

**Goal:** Wrap existing SmartAPI services in new interface

**Tasks:**
1. ✅ Create `SmartAPIMarketDataAdapter` implementing `MarketDataBrokerAdapter`
   - Wrap `smartapi_market_data.py` (REST quotes)
   - Wrap `smartapi_historical.py` (OHLCV)
   - Wrap `smartapi_instruments.py` (instruments)
   - Add symbol conversion (Angel format → Canonical)
   - Add price normalization (PAISE → RUPEES for WebSocket)

2. ✅ Update `SmartAPITickerService` to implement `TickerService` interface
   - Ensure all abstract methods implemented
   - Add reconnection logic
   - Add error callbacks

3. ✅ Create `market_data_factory.py`
   ```python
   async def get_market_data_adapter(broker_type: str, user_id: UUID, db) -> MarketDataBrokerAdapter:
       """Factory to get market data adapter."""
       # Implementation
   ```

4. ✅ Test with existing screens
   - Watchlist should work with SmartAPI adapter
   - Option Chain should work with SmartAPI adapter
   - No functionality regression

**Deliverables:**
- SmartAPI fully wrapped in abstraction
- Factory pattern working
- Existing features work via adapter

---

### Phase 3: Kite Adapter (Week 2)

**Goal:** Add Kite as second broker option

**Tasks:**
1. ✅ Create `KiteMarketDataAdapter` implementing `MarketDataBrokerAdapter`
   - REST quote API
   - Historical data API
   - Instruments API
   - Symbol already in canonical format (Kite format is canonical)

2. ✅ Create `KiteTickerService` implementing `TickerService` interface
   - Wrap existing `kite_ticker.py` logic
   - Ensure interface compliance

3. ✅ Test broker switching (SmartAPI ↔ Kite)
   - Change user preference
   - Verify WebSocket switches
   - Verify REST API switches
   - All screens should work seamlessly

**Deliverables:**
- Kite adapter complete
- Broker switching functional
- E2E test for switching

---

### Phase 4: Route Refactoring (Week 3)

**Goal:** Replace hardcoded broker logic with factory pattern

**Tasks:**
1. ✅ Refactor `websocket.py`
   ```python
   # OLD:
   if market_data_source == "smartapi":
       ticker = smartapi_ticker
   else:
       ticker = kite_ticker

   # NEW:
   ticker = get_ticker_service(user.preferences.market_data_source, credentials)
   ```

2. ✅ Refactor `optionchain.py`
   - Remove conditional logic
   - Use `get_market_data_adapter()`

3. ✅ Refactor `watchlist.py` (if needed)

4. ✅ Refactor any other routes with hardcoded broker logic

**Deliverables:**
- All routes use factory pattern
- No hardcoded broker conditionals
- All E2E tests pass

---

### Phase 5: Settings UI (Week 3)

**Goal:** Add broker selection UI and credential management

**Tasks:**
1. ✅ Update `SettingsView.vue`
   - Add broker selection dropdown
   - Add test connection button
   - Add save button with WebSocket refresh

2. ✅ Create market data API routes
   - `/api/market-data/test-connection`
   - `/api/market-data/switch-broker`
   - `/api/market-data/current-broker`

3. ✅ Update `api.js` with broker endpoints

4. ✅ Add E2E tests
   - Test broker selection
   - Test connection test
   - Test switching (SmartAPI → Kite → SmartAPI)

**Deliverables:**
- Settings UI complete
- User can switch brokers via UI
- WebSocket auto-reconnects with new broker

---

### Phase 6: Additional Brokers (Week 4+)

**Goal:** Add remaining 4 brokers one by one

**For each broker (Upstox, Dhan, Fyers, Paytm):**

1. ✅ Create credentials table
2. ✅ Implement `{Broker}MarketDataAdapter`
3. ✅ Implement `{Broker}TickerService`
4. ✅ Add to factory registry
5. ✅ Test connection
6. ✅ Test with all screens
7. ✅ Add to Settings UI dropdown

**Order of implementation:**
1. **Upstox** (most similar to Kite)
2. **Dhan** (good documentation)
3. **Fyers** (robust API)
4. **Paytm** (uses security_id instead of symbols)

---

### Phase 7: Token Population (Week 5)

**Goal:** Populate `broker_instrument_tokens` table

**Tasks:**
1. ✅ Create instrument download service
   ```python
   # backend/app/services/instrument_downloader.py
   async def download_instruments(broker: str):
       """Download and store instruments for broker."""
   ```

2. ✅ Create scheduled job (daily 6 AM IST)
   ```python
   # backend/app/tasks/daily_instrument_update.py
   async def update_all_broker_instruments():
       """Download instruments from all brokers."""
   ```

3. ✅ Add cleanup job for expired contracts
   ```python
   async def cleanup_expired_instruments():
       """Delete instruments past expiry."""
   ```

**Deliverables:**
- Token mapping table populated
- Daily refresh scheduled
- Expired contracts cleaned up

---

### Testing Strategy

**Unit Tests:**
- SymbolConverter parsing/formatting (6 brokers × 2 tests = 12 tests)
- UnifiedQuote normalization
- Rate limiter logic
- Token manager expiry checks

**Integration Tests:**
- Each adapter's connect/disconnect
- Quote fetching per broker
- Historical data retrieval
- WebSocket tick normalization

**E2E Tests:**
- Broker switching flow (Settings → WebSocket reconnect → Screens update)
- Screen data display after switch
- Error handling (invalid credentials, API down)
- Rate limit handling

**Performance Tests:**
- WebSocket tick latency per broker
- Symbol conversion speed (10,000 symbols)
- Token lookup speed (with/without Redis cache)

---

### Critical Success Metrics

**Functionality:**
- ✅ All 6 brokers connect successfully
- ✅ All screens work with any broker
- ✅ Switching takes < 5 seconds
- ✅ Zero code changes when adding broker #7

**Performance:**
- ✅ Symbol conversion < 1ms per symbol
- ✅ Token lookup < 10ms (with cache < 1ms)
- ✅ WebSocket tick latency < 100ms

**Reliability:**
- ✅ Auto-reconnect on WebSocket disconnect
- ✅ Token auto-refresh before expiry
- ✅ Graceful fallback on broker API errors

---

## Related Documentation

- [Broker Abstraction Architecture](./broker-abstraction.md) - Overall multi-broker system
- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) - Decision rationale
- [WebSocket Architecture](./websocket.md) - Live price streaming
- [Database Schema](./database.md) - Broker token mapping tables
- [Implementation Checklist](../IMPLEMENTATION-CHECKLIST.md) - Current implementation status
- [Developer Quick Reference](../DEVELOPER-QUICK-REFERENCE.md) - Development patterns

---

**Document Version:** 2.0
**Last Updated:** 2025-01-14
**Status:** Complete Implementation Guide

**This document includes:**
- ✅ Complete Settings UI with Vue 3 component
- ✅ Backend API endpoints for broker management
- ✅ 7-phase implementation roadmap with detailed tasks
- ✅ Testing strategy (unit, integration, E2E, performance)
- ✅ Critical success metrics
- ✅ Week-by-week breakdown
