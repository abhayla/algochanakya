---
name: store-action-result-objects
description: >
  Store actions serving per-call or modal-scoped data MUST return
  {success, data, error} result objects instead of mutating store refs.
globs: ["frontend/src/stores/*.js"]
synthesized: true
version: "1.0.0"
private: false
---

# Store Action Result Objects

Store actions that serve **per-call data** — data consumed once by the calling
modal or component and that should NOT persist in store state — MUST return a
`{success, data, error}` result object instead of mutating store refs.

The canonical form is the **parameterized-helpers section of `autopilot.js`**
(~lines 1727-1844): `fetchExpiriesFor(ul)`, `fetchStrikesFor(ul, expiry)`,
`fetchOrderLTP(params)`, and friends.

## Decision Boundary

- **Data shared across components/sessions** → store refs (the standard
  loading/error/data triple per `pinia-store-composition.md`)
- **Data consumed once by the calling modal** (parameterized lookups, previews,
  per-call quotes) → result object, NO store mutation

## Canonical Form (from `autopilot.js`)

```javascript
async fetchOrderLTP(params) {
  try {
    const response = await api.get('/api/orders/ltp', { params })
    return { success: true, data: response.data }
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message,
      data: null,
    }
  }
},
```

Parameterized list helpers may name the payload key after the resource —
`fetchExpiriesFor(ul)` returns `{ success: true, expiries }` and on failure
`{ success: false, error, expiries: [] }` — but the `success` flag and `error`
field are non-negotiable.

```javascript
async fetchExpiriesFor(ul) {
  try {
    const response = await api.get('/api/options/expiries', {
      params: { underlying: ul },
    })
    const data = response.data?.expiries ?? response.data ?? []
    return { success: true, expiries: data }
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message,
      expiries: [],
    }
  }
},
```

## Why

- Two components opening the same modal with different params would otherwise
  race on a shared store ref — result objects make each call self-contained
- Callers get explicit, local error handling (`if (!result.success) ...`)
  instead of watching a shared `error` ref that any action can overwrite
- No stale per-call data lingers in store state after the modal closes

Note: `simulateAdjustment` / `compareScenarios` (~lines 1683-1720) are also
per-call actions but predate this convention — they still mutate
`whatIfSimulation` state and throw on error. Do NOT copy that shape for new
per-call actions; the parameterized helpers below them are the model.

## CRITICAL RULES

- Per-call/modal-scoped actions MUST return `{success, data, error}` (or the
  resource-named variant: `{success, <resource>, error}` on the same shape)
- Per-call actions MUST NOT mutate store refs with their payload — the result
  object IS the delivery mechanism
- Per-call actions MUST catch their own errors and return
  `{ success: false, error, data: null }` — NEVER let the error propagate
  unhandled and NEVER write it to a shared store `error` ref
- Callers MUST check `result.success` before using `result.data`
- Data needed by more than one component or across sessions MUST go through
  store refs instead — do NOT use result objects to bypass shared state
