---
description: >
  Enforces consistent Pinia store composition patterns across all Vue stores.
  All stores MUST use the loading/error/data triple pattern and expose named action functions.
globs: ["frontend/src/stores/**/*.js", "frontend/src/stores/**/*.ts"]
synthesized: true
private: false
version: "1.1.0"
---

# Pinia Store Composition Pattern

All Pinia stores in `frontend/src/stores/` follow a consistent composition pattern. This convention ensures predictable state management across the application.

## Required Pattern

Every store MUST follow this structure:

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFeatureStore = defineStore('feature', () => {
  // --- State: use ref() for each piece of state ---
  const data = ref(null)        // Primary data
  const loading = ref(false)    // Loading indicator
  const error = ref(null)       // Error state

  // --- Actions: named async functions ---
  async function fetchData() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/endpoint')
      data.value = response.data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  // --- Return all state and actions ---
  return { data, loading, error, fetchData }
})
```

## Conventions Observed Across All Stores

### State Declaration

- MUST use `ref()` for individual state properties — not `reactive()` for the entire state object
- MUST include the **loading/error/data triple**: every store that fetches data needs `loading`, `error`, and the primary data ref
- For stores with multiple async operations, use operation-specific loading refs (e.g., `zerodhaLoading`, `angelOneLoading` as seen in `auth.js`)

### Per-Feature Loading Refs (hardened post store-migration, April 2026)

In multi-section stores, each async action MUST get its OWN dedicated loading ref.
A single global `loading` ref is no longer acceptable for stores that serve more
than one UI section — unrelated sections must be able to load independently
without blocking each other's spinners.

Canonical example — `aiAnalytics.js` (lines 5-12): five separate refs, one per
feature area, all returned explicitly in the return block:

```javascript
export const useAIAnalyticsStore = defineStore('aiAnalytics', () => {
  // Per-feature loading refs (keep UI sections unblocked from each other)
  const autonomyLoading = ref(false)
  const capitalRiskLoading = ref(false)
  const regimeStrengthsLoading = ref(false)
  const analyticsLoading = ref(false)
  const paperTradingLoading = ref(false)
  const error = ref(null)
  // ...
  return {
    autonomyLoading,
    capitalRiskLoading,
    regimeStrengthsLoading,
    analyticsLoading,
    paperTradingLoading,
    // ...
  }
})
```

- Each ref MUST be named `<feature>Loading` and set/cleared only by its own action(s)
- Every loading ref MUST be returned explicitly in the return block — no implicit exposure
- Older stores (e.g., `brokerPreferences.js`) predate this convention and are
  grandfathered; do NOT copy their single-`loading` shape into new or migrated stores

### Action Functions

- MUST be named functions (`async function fetchData()`) — not arrow functions assigned to variables
- MUST set `loading = true` at the start and `loading = false` in `finally`
- MUST clear `error = null` before each operation attempt
- MUST catch errors and store them in the `error` ref — do NOT let errors propagate unhandled

### Store Naming

- Store ID (first arg to `defineStore`) MUST match the filename without extension: `useAuthStore` → `defineStore('auth', ...)` in `auth.js`
- Export name MUST follow `use<Feature>Store` pattern

## Evidence From Existing Stores

| Store | Loading refs | Error ref | Named actions |
|-------|-------------|-----------|---------------|
| `auth.js` | `loading`, `zerodhaLoading`, `angelOneLoading`, etc. (7 refs) | implicit | `login()`, `fetchUser()`, `logout()` |
| `autopilot.js` | `loading`, `saving` | `error` | async actions via state |
| `brokerPreferences.js` | `loading`, `saving` | `error` | `updatePreferences()` |
| `optionchain.js` | `isLoading` | `error` | `fetchOptionChain()`, `setUnderlying()` |
| `aiConfig.js` | `loading`, `saving` | `error`, `validationErrors` | async actions |

## Anti-Patterns

- MUST NOT use `reactive()` for the top-level store state — it breaks reactivity when destructuring in components
- MUST NOT expose raw API calls from stores — wrap in actions with loading/error handling
- MUST NOT share store instances between components via props — each component should `useFeatureStore()` independently
- MUST NOT mutate store state directly from components — always go through store actions
