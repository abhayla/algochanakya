---
description: >
  Frontend data flow convention: views import stores and composables only, stores handle
  all API calls via the api service, components never import api.js directly.
globs: ["frontend/src/**/*.{vue,js}"]
synthesized: true
private: false
---

# Frontend Data Flow

## Three-Layer Architecture

```
Views/Components  →  Stores (Pinia)  →  API Service (Axios)
       ↓                   ↓                    ↓
  UI rendering      State + logic         HTTP requests
  User events       Computed values       Token injection
  Store access      Error handling        401 handling
```

## Views: Store and Composable Access Only

Views and components MUST access data through Pinia stores or composables.
They MUST NOT import `api` from `@/services/api` directly.

```javascript
// CORRECT — view uses store:
import { useOptionChainStore } from '@/stores/optionchain'
import { useScrollIndicator } from '@/composables/useScrollIndicator'

const store = useOptionChainStore()
await store.fetchOptionChain(symbol, expiry)

// WRONG — view calls API directly:
import api from '@/services/api'
const { data } = await api.get('/api/optionchain/...')  // NEVER in views
```

## Stores: Own All API Communication

Pinia stores encapsulate API calls, state management, and business logic.
Every store that fetches data imports `api` from `@/services/api`:

```javascript
// stores/optionchain.js
import api from '../services/api'

export const useOptionChainStore = defineStore('optionchain', () => {
  const chain = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  async function fetchOptionChain(symbol, expiry) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await api.get(`/api/optionchain/${symbol}/${expiry}`)
      chain.value = data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to load'
    } finally {
      isLoading.value = false
    }
  }

  return { chain, isLoading, error, fetchOptionChain }
})
```

## Per-Feature Loading States

Each store MUST maintain feature-specific loading and error refs — not a single
global loading flag. This prevents unrelated UI sections from blocking each other.

```javascript
// CORRECT — per-feature loading:
const optionChain = ref({ loading: false, error: null })
const strikeFinder = ref({ loading: false, error: null })
const suggestions = ref({ loading: false, error: null })

// WRONG — single global loading:
const loading = ref(false)  // Blocks entire store UI during any operation
```

## Composables: Reusable UI Logic

Composables (`src/composables/`) abstract reusable reactive logic that doesn't
need store persistence. Use composables for:
- UI behavior (scroll indicators, toasts, WebSocket connections)
- Derived computations shared across components
- DOM event management

Composables MUST NOT call API endpoints directly — delegate to stores if data
fetching is needed.

## Why This Matters

- Single point for API error handling and token injection (in `api.js` interceptors)
- Stores are testable with mocked API — no component-level API mocking needed
- Consistent loading/error state management across all features
- Clear separation: views render, stores manage state, api handles transport

## MUST NOT

- MUST NOT import `api` or `axios` in view/component files
- MUST NOT use a single loading flag for multiple async operations in a store
- MUST NOT put API calls in composables — composables are for UI logic only
