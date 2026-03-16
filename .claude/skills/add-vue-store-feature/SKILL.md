---
name: add-vue-store-feature
description: >
  Add a new Pinia store or feature module to the Vue frontend with proper
  API integration, composables, and Vitest tests.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<store-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add Vue Store Feature

## STEP 1: Create Pinia Store

Create `frontend/src/stores/<name>.js`:

```javascript
import { defineStore } from 'pinia'
import api from '@/services/api'

export const use<Name>Store = defineStore('<name>', {
  state: () => ({
    data: null,
    loading: false,
    error: null,
  }),
  getters: {
    hasData: (state) => state.data !== null,
  },
  actions: {
    async fetchData() {
      this.loading = true
      this.error = null
      try {
        const response = await api.get('/<endpoint>')
        this.data = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
      } finally {
        this.loading = false
      }
    },
  },
})
```

## STEP 2: Use api.js for HTTP

MUST use `import api from '@/services/api'` -- never raw axios. The shared api.js instance has auth interceptors and base URL configuration.

## STEP 3: Create Composable (Optional)

For complex reactive logic, create `frontend/src/composables/use<Name>.js`.

## STEP 4: Integrate with View

Import store in the relevant view component. Use `storeToRefs()` for reactive access.

## STEP 5: Add data-testid Attributes

All interactive elements in new components MUST have data-testid for E2E testing.

## STEP 6: Write Vitest Tests

Create `frontend/tests/stores/<name>.test.js`:

```javascript
import { setActivePinia, createPinia } from 'pinia'
import { use<Name>Store } from '@/stores/<name>'

beforeEach(() => setActivePinia(createPinia()))

test('fetches data', async () => {
  const store = use<Name>Store()
  // Mock api calls, test actions and state changes
})
```

## CRITICAL RULES

- NEVER import axios directly -- always use @/services/api
- Use defineStore with options API (consistent with existing stores)
- Add data-testid to all interactive elements
- Use getLotSize() from @/constants/trading for lot sizes, never hardcode
- Clean up WebSocket subscriptions in onUnmounted()
