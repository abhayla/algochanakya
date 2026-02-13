# Phase 1 Component Status & Integration Guide

## Component Inventory

### ✅ Completed Components

| Component | Type | Location | Status |
|-----------|------|----------|--------|
| **OrderExecutor Integration** | Backend Service | `backend/app/services/order_executor.py` | ✅ Complete |
| **StrikeFinderService Integration** | Backend Service | `backend/app/services/leg_actions_service.py` | ✅ Complete |
| **Strike Preview API** | Backend Endpoint | `backend/app/api/v1/autopilot/router.py:314` | ✅ Complete |
| **Strike Schemas** | Backend Schema | `backend/app/schemas/autopilot.py:1745` | ✅ Complete |
| **StrikeSelector** | Frontend Component | `frontend/src/components/autopilot/builder/StrikeSelector.vue` | ✅ Complete |
| **StrikeLadder** | Frontend Component | `frontend/src/components/autopilot/builder/StrikeLadder.vue` | ✅ Complete |

---

## Integration Status

### ✅ Integrated Components

| Component | Integrated Into | Status | Date |
|-----------|-----------------|--------|------|
| **StrikeLadder** | `AutoPilotLegsTable.vue` (Modal) | ✅ Integrated | Dec 17, 2025 |

### 🔄 Optional Future Enhancements

| Component | Potential Integration | Priority |
|-----------|----------------------|----------|
| **StrikeSelector** | Replace inline strike selection in leg rows | Low |

### ✅ StrikeLadder Integration (Completed)

**Location:** `frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue`

**How it works:**
1. Each leg row has a green grid icon button next to the strike mode dropdown
2. Clicking the button opens a modal with the StrikeLadder component
3. User can browse strikes with live delta, LTP, and Greeks
4. Clicking CE/PE buttons selects that strike for the leg
5. Modal closes and strike is populated in the leg

**Code Example:**
```vue
<!-- AutoPilotLegsTable.vue -->
<template>
  <div>
    <!-- Leg rows with strike ladder button -->
    <AutoPilotLegRow
      v-for="(leg, index) in legs"
      :key="leg.id"
      @open-strike-ladder="openStrikeLadder"
    />

    <!-- StrikeLadder Modal -->
    <div v-if="showStrikeLadder" class="modal-overlay">
      <StrikeLadder
        :underlying="strategy.underlying"
        :expiry="currentLeg.expiry_date"
        :spot-price="currentSpotPrice"
        @strike-selected="onStrikeSelected"
      />
    </div>
  </div>
</template>
```

---

### How Components Should Be Used (Legacy Reference)

```vue
<!-- Example for manual integration elsewhere -->

<template>
  <div class="legs-config">
    <!-- For each leg -->
    <div class="leg-row">
      <select v-model="leg.contract_type">
        <option value="CE">CE</option>
        <option value="PE">PE</option>
      </select>

      <select v-model="leg.transaction_type">
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>

      <!-- INTEGRATE StrikeSelector HERE -->
      <StrikeSelector
        :underlying="strategy.underlying"
        :expiry="strategy.expiry_date"
        :option-type="leg.contract_type"
        v-model="leg.strike_selection"
        @input="onStrikeConfigChange(leg)"
      />

      <!-- Or, add button to open StrikeLadder -->
      <button @click="openStrikeLadder(leg)">
        Select from Ladder
      </button>
    </div>

    <!-- StrikeLadder Modal -->
    <Modal v-if="showLadder" @close="showLadder = false">
      <StrikeLadder
        :underlying="strategy.underlying"
        :expiry="strategy.expiry_date"
        :spot-price="currentSpotPrice"
        @strike-selected="onStrikeSelected"
      />
    </Modal>
  </div>
</template>

<script>
import StrikeSelector from '@/components/autopilot/builder/StrikeSelector.vue'
import StrikeLadder from '@/components/autopilot/builder/StrikeLadder.vue'

export default {
  components: { StrikeSelector, StrikeLadder },
  data() {
    return {
      showLadder: false,
      currentLeg: null
    }
  },
  methods: {
    onStrikeConfigChange(leg) {
      // Strike selection config changed
      // leg.strike_selection now has: { mode, target_delta, etc. }
      console.log('Strike config:', leg.strike_selection)
    },
    openStrikeLadder(leg) {
      this.currentLeg = leg
      this.showLadder = true
    },
    onStrikeSelected(strikeData) {
      // User selected strike from ladder
      // strikeData = { strike, optionType, ltp, delta, gamma, theta, iv }
      this.currentLeg.strike_selection = {
        mode: 'fixed',
        fixed_strike: strikeData.strike
      }
      this.currentLeg.entry_price = strikeData.ltp
      this.showLadder = false
    }
  }
}
</script>
```

---

## Testing Each Component Individually

### Test 1: StrikeSelector (Isolated)

**Create test file:** `frontend/src/views/TestStrikeSelector.vue`

```vue
<template>
  <div style="padding: 24px; max-width: 600px;">
    <h2>StrikeSelector Test</h2>
    <StrikeSelector
      underlying="NIFTY"
      expiry="2024-12-26"
      option-type="CE"
      v-model="strikeConfig"
      @input="onConfigChange"
    />
    <pre>{{ strikeConfig }}</pre>
  </div>
</template>

<script>
import StrikeSelector from '@/components/autopilot/builder/StrikeSelector.vue'

export default {
  components: { StrikeSelector },
  data() {
    return {
      strikeConfig: {
        mode: 'delta_based',
        target_delta: 0.30,
        prefer_round_strike: true
      }
    }
  },
  methods: {
    onConfigChange(val) {
      console.log('Config changed:', val)
    }
  }
}
</script>
```

**Access:** `http://localhost:5173/test-strike-selector`

### Test 2: StrikeLadder (Isolated)

**Create test file:** `frontend/src/views/TestStrikeLadder.vue`

```vue
<template>
  <div style="padding: 24px;">
    <h2>StrikeLadder Test</h2>
    <StrikeLadder
      underlying="NIFTY"
      expiry="2024-12-26"
      :spot-price="24200"
      @strike-selected="onStrikeSelected"
    />
    <div v-if="selected" style="margin-top: 24px; padding: 16px; background: #f0f9ff; border-radius: 8px;">
      <strong>Selected:</strong> {{ selected.strike }} {{ selected.optionType }} @ ₹{{ selected.ltp }}
    </div>
  </div>
</template>

<script>
import StrikeLadder from '@/components/autopilot/builder/StrikeLadder.vue'

export default {
  components: { StrikeLadder },
  data() {
    return {
      selected: null
    }
  },
  methods: {
    onStrikeSelected(data) {
      this.selected = data
      console.log('Strike selected:', data)
    }
  }
}
</script>
```

**Access:** `http://localhost:5173/test-strike-ladder`

---

## API Endpoint Testing

### cURL Test Commands

```bash
# Set your JWT token
TOKEN="your_jwt_token_here"

# Test 1: Delta-based
curl -X GET "http://localhost:8000/api/v1/autopilot/strikes/preview?underlying=NIFTY&expiry=2024-12-26&option_type=CE&mode=delta_based&target_delta=0.30&prefer_round_strike=true" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Test 2: Premium-based
curl -X GET "http://localhost:8000/api/v1/autopilot/strikes/preview?underlying=NIFTY&expiry=2024-12-26&option_type=PE&mode=premium_based&target_premium=100&prefer_round_strike=true" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Test 3: SD-based
curl -X GET "http://localhost:8000/api/v1/autopilot/strikes/preview?underlying=BANKNIFTY&expiry=2024-12-26&option_type=CE&mode=sd_based&standard_deviations=1.5&outside_sd=true&prefer_round_strike=true" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Test 4: Error case (invalid mode)
curl -X GET "http://localhost:8000/api/v1/autopilot/strikes/preview?underlying=NIFTY&expiry=2024-12-26&option_type=CE&mode=invalid" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

### Postman Collection

```json
{
  "info": {
    "name": "Phase 1 Strike Selection Tests",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Delta-Based Strike Preview",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/autopilot/strikes/preview?underlying=NIFTY&expiry=2024-12-26&option_type=CE&mode=delta_based&target_delta=0.30&prefer_round_strike=true",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "autopilot", "strikes", "preview"],
          "query": [
            {"key": "underlying", "value": "NIFTY"},
            {"key": "expiry", "value": "2024-12-26"},
            {"key": "option_type", "value": "CE"},
            {"key": "mode", "value": "delta_based"},
            {"key": "target_delta", "value": "0.30"},
            {"key": "prefer_round_strike", "value": "true"}
          ]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "jwt_token",
      "value": "your_token_here"
    }
  ]
}
```

---

## File Checklist

**Verify these files exist:**

```bash
# Backend files
backend/app/services/order_executor.py (modified)
backend/app/services/leg_actions_service.py (modified)
backend/app/schemas/autopilot.py (modified)
backend/app/api/v1/autopilot/router.py (modified)
backend/test_phase1_strike_selection.py (new)

# Frontend files
frontend/src/components/autopilot/builder/StrikeSelector.vue (new)
frontend/src/components/autopilot/builder/StrikeLadder.vue (new)

# Documentation files
docs/autopilot/AutoPilot-Redesign-Implementation-Plan.md (modified)
docs/autopilot/Phase-1-Testing-Guide.md (new)
docs/autopilot/Phase-1-Component-Status.md (new)
PHASE1_TESTING_SUMMARY.md (new)
```

**Quick check:**
```bash
# From project root
ls -la backend/app/services/order_executor.py
ls -la backend/app/schemas/autopilot.py
ls -la backend/app/api/v1/autopilot/router.py
ls -la frontend/src/components/autopilot/builder/StrikeSelector.vue
ls -la frontend/src/components/autopilot/builder/StrikeLadder.vue
```

---

## Common Issues & Solutions

### Issue 1: "Cannot find module 'StrikeSelector'"

**Cause:** Component not imported or path wrong

**Solution:**
```javascript
import StrikeSelector from '@/components/autopilot/builder/StrikeSelector.vue'
```

### Issue 2: "API returns 401 Unauthorized"

**Cause:** No JWT token or expired token

**Solution:** Login first, get fresh token from localStorage

### Issue 3: "Preview shows 'Loading...' forever"

**Cause:** API call failing silently

**Solution:** Open browser console, check Network tab for errors

### Issue 4: "Strike Finder returns None"

**Cause:** No option chain data for selected expiry

**Solution:** Choose a current week expiry with active options

---

## Integration Priority

**Phase 1.5 (Optional - Before Phase 2):**

1. **High Priority:** Integrate StrikeSelector into legs table
2. **Medium Priority:** Add StrikeLadder modal/button
3. **Low Priority:** Add strike preview in leg row

**Time Estimate:** 1-2 hours for full integration

---

## Success Criteria for Testing

**Phase 1 testing is successful when:**

✅ All API endpoints return 200 for valid requests
✅ StrikeSelector renders without errors
✅ Preview panel shows real data from API
✅ Mode switching works smoothly
✅ Quick-select presets update preview
✅ StrikeLadder displays option chain
✅ Strike selection emits correct events
✅ No console errors in browser
✅ No backend errors in logs

---

**Status:** Ready for Testing 🚀
**Last Updated:** December 17, 2025
